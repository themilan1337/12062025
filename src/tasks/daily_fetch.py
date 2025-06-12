import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import aiohttp
from celery import Celery
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from redis_client import redis_client

logger = logging.getLogger(__name__)


async def fetch_website_data(url: str) -> Dict[str, Any]:
    """Fetch data from a website"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    # For JSON APIs
                    if 'application/json' in response.headers.get('content-type', ''):
                        data = await response.json()
                    else:
                        # For HTML or text content
                        text_content = await response.text()
                        data = {
                            'content': text_content[:5000],  # Limit content size
                            'content_type': response.headers.get('content-type', 'text/html'),
                            'status_code': response.status
                        }
                    
                    return {
                        'success': True,
                        'data': data,
                        'url': url,
                        'fetched_at': datetime.utcnow().isoformat(),
                        'status_code': response.status
                    }
                else:
                    logger.error(f"Failed to fetch data from {url}: HTTP {response.status}")
                    return {
                        'success': False,
                        'error': f"HTTP {response.status}",
                        'url': url,
                        'fetched_at': datetime.utcnow().isoformat()
                    }
    except asyncio.TimeoutError:
        logger.error(f"Timeout while fetching data from {url}")
        return {
            'success': False,
            'error': 'Timeout',
            'url': url,
            'fetched_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return {
            'success': False,
            'error': str(e),
            'url': url,
            'fetched_at': datetime.utcnow().isoformat()
        }


async def save_fetched_data_to_db(data: Dict[str, Any]) -> bool:
    """Save fetched data to database"""
    try:
        async with get_async_session() as db:
            # Create table if it doesn't exist
            create_table_query = text("""
                CREATE TABLE IF NOT EXISTS daily_fetched_data (
                    id SERIAL PRIMARY KEY,
                    url VARCHAR(500) NOT NULL,
                    data JSONB NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute(create_table_query)
            
            # Insert the fetched data
            insert_query = text("""
                INSERT INTO daily_fetched_data 
                (url, data, success, error_message, fetched_at)
                VALUES (:url, :data, :success, :error_message, :fetched_at)
            """)
            
            await db.execute(insert_query, {
                'url': data['url'],
                'data': data,
                'success': data['success'],
                'error_message': data.get('error'),
                'fetched_at': datetime.fromisoformat(data['fetched_at'].replace('Z', '+00:00'))
            })
            
            await db.commit()
            logger.info(f"Successfully saved data from {data['url']} to database")
            return True
            
    except Exception as e:
        logger.error(f"Error saving data to database: {e}")
        return False


async def cache_fetched_data(data: Dict[str, Any], cache_key: str, expire_seconds: int = 86400):
    """Cache fetched data in Redis"""
    try:
        import json
        await redis_client.set(cache_key, json.dumps(data), ex=expire_seconds)
        logger.info(f"Cached data with key: {cache_key}")
    except Exception as e:
        logger.error(f"Error caching data: {e}")


def daily_fetch_task(urls: list = None):
    """Celery task to fetch data from websites daily"""
    if urls is None:
        # Default URLs to fetch data from
        urls = [
            "https://jsonplaceholder.typicode.com/posts/1",  # Example JSON API
            "https://httpbin.org/json",  # Another example API
            "https://api.github.com/repos/python/cpython",  # GitHub API example
        ]
    
    async def run_fetch_tasks():
        results = []
        for url in urls:
            try:
                # Fetch data from website
                data = await fetch_website_data(url)
                results.append(data)
                
                # Save to database
                await save_fetched_data_to_db(data)
                
                # Cache the data
                cache_key = f"daily_fetch:{url.replace('/', '_').replace(':', '_')}"
                await cache_fetched_data(data, cache_key)
                
                logger.info(f"Processed URL: {url}, Success: {data['success']}")
                
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'url': url,
                    'fetched_at': datetime.utcnow().isoformat()
                })
        
        return results
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(run_fetch_tasks())
        logger.info(f"Daily fetch task completed. Processed {len(results)} URLs")
        return {
            'task': 'daily_fetch_task',
            'completed_at': datetime.utcnow().isoformat(),
            'results': results,
            'total_urls': len(urls),
            'successful_fetches': sum(1 for r in results if r.get('success', False))
        }
    finally:
        loop.close()


def get_cached_data(url: str):
    """Get cached data for a URL"""
    try:
        import json
        cache_key = f"daily_fetch:{url.replace('/', '_').replace(':', '_')}"
        
        # Use sync Redis client for Celery task
        import redis
        from config import settings
        sync_redis = redis.from_url(settings.redis_url)
        
        cached_data = sync_redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        return None
    except Exception as e:
        logger.error(f"Error getting cached data: {e}")
        return None