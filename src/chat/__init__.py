"""
Chat module for WebSocket-based real-time messaging.

This module provides:
- WebSocket connections for real-time chat
- Chat room management
- Message persistence
- User presence tracking
"""

from .api import router
from .models import ChatRoom as ChatRoomSchema
from .models import ChatRoomCreate, ChatRoomUpdate
from .models import Message as MessageSchema
from .models import MessageCreate, RoomWithMessages, WebSocketMessage
from .schema import ChatParticipant, ChatRoom, Message
from .websocket_manager import manager

__all__ = [
    "ChatRoom", "Message", "ChatParticipant",
    "ChatRoomCreate", "ChatRoomUpdate", "ChatRoomSchema",
    "MessageCreate", "MessageSchema", "WebSocketMessage", "RoomWithMessages",
    "manager", "router"
]
