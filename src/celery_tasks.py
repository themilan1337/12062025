from celery import current_app
from celery_app import celery_app
from redis_client import redis_client
import time
import logging
from tasks.tasks import add_random_task, add_multiple_random_tasks
from tasks.daily_fetch import daily_fetch_task

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def example_task(self, name: str):
    """
    Example Celery task that demonstrates basic functionality
    """
    try:
        logger.info(f"Starting task for {name}")
        
        # Simulate some work
        time.sleep(2)
        # Store result in Redis
        redis_client.setex(f"task_result_{self.request.id}", 3600, f"Hello {name}!")
        
        logger.info(f"Task completed for {name}")
        return f"Task completed for {name}"
    
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task
def send_notification(message: str, recipient: str):
    """
    Example task for sending notifications
    """
    logger.info(f"Sending notification to {recipient}: {message}")
    # Simulate notification sending
    time.sleep(1)
    return f"Notification sent to {recipient}"

@celery_app.task
def process_data(data: dict):
    """
    Example task for data processing
    """
    logger.info(f"Processing data: {data}")
    
    # Simulate data processing
    time.sleep(3)
    
    # Store processed data in Redis
    processed_key = f"processed_data_{int(time.time())}"
    redis_client.setex(processed_key, 3600, str(data))
    
    return {
        "status": "processed",
        "data": data,
        "key": processed_key
    }

@celery_app.task
def cleanup_old_data():
    """
    Example periodic task for cleanup operations
    """
    logger.info("Running cleanup task")
    
    # Example: Clean up old Redis keys
    # This is just an example - implement your actual cleanup logic
    keys_deleted = 0
    for key in redis_client.scan_iter(match="temp_*"):
        redis_client.delete(key)
        keys_deleted += 1
    
    logger.info(f"Cleanup completed. Deleted {keys_deleted} keys")
    return f"Cleaned up {keys_deleted} temporary keys"

@celery_app.task
def trigger_random_task_creation():
    """Trigger creation of multiple random tasks"""
    try:
        result = add_multiple_random_tasks.delay(5)  # Create 5 random tasks
        logger.info(f"Triggered creation of multiple random tasks: {result.id}")
        return f"Task creation triggered: {result.id}"
    except Exception as e:
        logger.error(f"Error triggering random task creation: {e}")
        return f"Error: {e}"


@celery_app.task
def daily_website_fetch(urls=None):
    """Daily task to fetch data from websites"""
    try:
        result = daily_fetch_task(urls)
        logger.info(f"Daily fetch task completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in daily fetch task: {e}")
        return {"error": str(e), "task": "daily_website_fetch"}

