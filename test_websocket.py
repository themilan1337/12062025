#!/usr/bin/env python3
"""
Простой тест WebSocket подключения для чата
"""

import asyncio
import json
import random

import websockets


async def test_websocket():
    # Параметры подключения
    room_id = 1
    user_id = random.randint(1, 1000)
    username = f"TestUser{user_id}"
    
    # URL WebSocket
    ws_url = f"ws://localhost:8000/chat/ws/{room_id}?user_id={user_id}&username={username}"
    
    print(f"Подключение к: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print(f"✅ Подключен как {username}")
            test_message = {
                "type": "message",
                "content": f"Привет от {username}!"
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"📤 Отправлено: {test_message['content']}")
            
            # Слушаем сообщения
            print("🔄 Ожидание сообщений...")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"📨 Получено: {data}")
                    
                    if data.get("type") == "user_list":
                        print(f"👥 Пользователи онлайн: {len(data.get('users', []))}")
                    
                    # Остановимся после получения нескольких сообщений
                    if data.get("type") == "message":
                        break
                        
                except json.JSONDecodeError:
                    print(f"❌ Ошибка парсинга JSON: {message}")
                    
    except Exception as e:
        print(f"❌ Ошибка WebSocket: {e}")

if __name__ == "__main__":
    print("🚀 Тест WebSocket чата")
    asyncio.run(test_websocket())
