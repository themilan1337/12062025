import json
import logging
from datetime import datetime
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Store active connections by room
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
        # Store user info for each connection
        self.user_connections: Dict[WebSocket, Dict[str, any]] = {}

    async def connect(
        self, websocket: WebSocket, room_id: int, user_id: int, username: str
    ):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user_id] = websocket
        self.user_connections[websocket] = {
            "user_id": user_id,
            "username": username,
            "room_id": room_id
        }

        logger.info(
            f"User {username} (ID: {user_id}) connected to room {room_id}"
        )
        await self.broadcast_to_room(room_id, {
            "type": "user_joined",
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.now().isoformat()
        }, exclude_user=user_id)
        await self.send_user_list(room_id)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.user_connections:
            user_info = self.user_connections[websocket]
            user_id = user_info["user_id"]
            username = user_info["username"]
            room_id = user_info["room_id"]
            if (room_id in self.active_connections and
                user_id in self.active_connections[room_id]):
                del self.active_connections[room_id][user_id]
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
            del self.user_connections[websocket]
            logger.info(
                f"User {username} (ID: {user_id}) disconnected from room {room_id}"
            )
            if room_id in self.active_connections:
                import asyncio
                asyncio.create_task(self.broadcast_to_room(room_id, {
                    "type": "user_left",
                    "user_id": user_id,
                    "username": username,
                    "timestamp": datetime.now().isoformat()
                }, exclude_user=user_id))
                asyncio.create_task(self.send_user_list(room_id))

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_room(
        self, room_id: int, message: dict, exclude_user: int = None
    ):
        if room_id not in self.active_connections:
            return
        message_text = json.dumps(message)
        disconnected_connections = []
        for user_id, connection in self.active_connections[room_id].items():
            if exclude_user and user_id == exclude_user:
                continue
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected_connections.append(connection)
        for connection in disconnected_connections:
            self.disconnect(connection)

    async def send_user_list(self, room_id: int):
        if room_id not in self.active_connections:
            return
        users = []
        for user_id, connection in self.active_connections[room_id].items():
            if connection in self.user_connections:
                user_info = self.user_connections[connection]
                users.append({
                    "user_id": user_info["user_id"],
                    "username": user_info["username"]
                })
        message = {
            "type": "user_list",
            "users": users,
            "room_id": room_id,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_room(room_id, message)

    def get_room_users(self, room_id: int) -> List[Dict]:
        if room_id not in self.active_connections:
            return []
        users = []
        for user_id, connection in self.active_connections[room_id].items():
            if connection in self.user_connections:
                user_info = self.user_connections[connection]
                users.append({
                    "user_id": user_info["user_id"],
                    "username": user_info["username"]
                })
        return users

    def get_connection_count(self, room_id: int = None) -> int:
        if room_id:
            return len(self.active_connections.get(room_id, {}))
        return sum(
            len(connections) for connections in self.active_connections.values()
        )


# Global connection manager instance
manager = ConnectionManager()
