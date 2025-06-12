import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import (APIRouter, Depends, HTTPException, Request, WebSocket,
                     WebSocketDisconnect)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth.api import get_current_user
from auth.models import User
from database import get_async_db

from .models import ChatRoom as ChatRoomSchema
from .models import ChatRoomCreate
from .models import Message as MessageSchema
from .models import MessageCreate, RoomWithMessages
from .schema import ChatParticipant, ChatRoom, Message
from .websocket_manager import manager
from .voice_chat import voice_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat")

# Get the absolute path to the templates directory
current_dir = Path(__file__).parent
templates_dir = current_dir / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# HTML Chat Demo endpoint
@router.get("/demo", response_class=HTMLResponse)
async def chat_demo(request: Request):
    """Serve the chat HTML demo page"""
    return templates.TemplateResponse("chat.html", {"request": request})


@router.get("/voice-demo", response_class=HTMLResponse)
async def voice_chat_demo(request: Request):
    """Serve the voice chat HTML demo page"""
    return templates.TemplateResponse("voice_chat.html", {"request": request})


# Chat Room endpoints
@router.post("/rooms", response_model=ChatRoomSchema)
async def create_chat_room(
    room_data: ChatRoomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new chat room"""
    room = ChatRoom(
        name=room_data.name,
        description=room_data.description,
        is_public=room_data.is_public
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    participant = ChatParticipant(
        room_id=room.id,
        user_id=current_user.id,
        is_admin=True
    )
    db.add(participant)
    await db.commit()

    return room


@router.get("/rooms", response_model=List[ChatRoomSchema])
async def get_chat_rooms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    stmt = select(ChatRoom).where(
        (ChatRoom.is_public.is_(True)) |
        (ChatRoom.id.in_(
            select(ChatParticipant.room_id).where(
                ChatParticipant.user_id == current_user.id
            )
        ))
    ).order_by(ChatRoom.created_at.desc())
    result = await db.execute(stmt)
    rooms = result.scalars().all()
    return rooms


@router.get("/rooms/{room_id}", response_model=RoomWithMessages)
async def get_chat_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    stmt = select(ChatRoom).options(
        selectinload(ChatRoom.messages),
        selectinload(ChatRoom.participants)
    ).where(ChatRoom.id == room_id)
    result = await db.execute(stmt)
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    if not room.is_public:
        participant_stmt = select(ChatParticipant).where(
            ChatParticipant.room_id == room_id,
            ChatParticipant.user_id == current_user.id
        )
        participant_result = await db.execute(participant_stmt)
        if not participant_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")

    return room


@router.post("/rooms/{room_id}/join")
async def join_chat_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Join a chat room"""
    # Check if room exists
    room_stmt = select(ChatRoom).where(ChatRoom.id == room_id)
    room_result = await db.execute(room_stmt)
    room = room_result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Check if already a participant
    participant_stmt = select(ChatParticipant).where(
        ChatParticipant.room_id == room_id,
        ChatParticipant.user_id == current_user.id
    )
    participant_result = await db.execute(participant_stmt)
    existing_participant = participant_result.scalar_one_or_none()
    
    if existing_participant:
        return {"message": "Already a participant in this room"}
    
    # Add as participant
    participant = ChatParticipant(
        room_id=room_id,
        user_id=current_user.id,
        is_admin=False
    )
    db.add(participant)
    await db.commit()
    
    return {"message": "Successfully joined the chat room"}


@router.post("/rooms/{room_id}/messages", response_model=MessageSchema)
async def create_message(
    room_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new message in a chat room"""
    # Check if user is participant
    participant_stmt = select(ChatParticipant).where(
        ChatParticipant.room_id == room_id,
        ChatParticipant.user_id == current_user.id
    )
    participant_result = await db.execute(participant_stmt)
    if not participant_result.scalar_one_or_none():
        raise HTTPException(
            status_code=403,
            detail="Not a participant in this room"
        )
    message = Message(
        content=message_data.content,
        room_id=room_id,
        user_id=current_user.id,
        message_type=message_data.message_type
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    await manager.broadcast_to_room(room_id, {
        "type": "message",
        "content": message.content,
        "user_id": current_user.id,
        "username": current_user.username,
        "message_id": message.id,
        "message_type": message.message_type,
        "timestamp": message.created_at.isoformat()
    })
    
    return message


# WebSocket endpoint
@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    user_id: int,
    username: str
):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, room_id, user_id, username)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                
                if message_data.get("type") == "message":
                    # Broadcast the message to all users in the room
                    await manager.broadcast_to_room(room_id, {
                        "type": "message",
                        "content": message_data.get("content"),
                        "user_id": user_id,
                        "username": username,
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_data.get("type") == "typing":
                    # Broadcast typing indicator (exclude sender)
                    await manager.broadcast_to_room(room_id, {
                        "type": "typing",
                        "user_id": user_id,
                        "username": username,
                        "is_typing": message_data.get("is_typing", False)
                    }, exclude_user=user_id)
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {user_id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid message format"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/rooms/{room_id}/users")
async def get_room_users(
    room_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get list of users currently connected to a room"""
    users = manager.get_room_users(room_id)
    return {"users": users, "count": len(users)}


@router.get("/stats")
async def get_chat_stats():
    """Get chat statistics"""
    total_connections = manager.get_connection_count()
    return {
        "total_connections": total_connections,
        "active_rooms": len(manager.active_connections)
    }


# Voice Chat endpoints
@router.websocket("/voice/{room_id}")
async def voice_chat_endpoint(
    websocket: WebSocket,
    room_id: int,
    user_id: int
):
    """WebSocket endpoint for voice chat with OpenAI Realtime API"""
    await websocket.accept()
    
    # Generate unique session ID
    session_id = f"voice_{room_id}_{user_id}_{uuid.uuid4().hex[:8]}"
    
    try:
        # Start voice session
        await voice_manager.start_voice_session(websocket, session_id, user_id)
    except WebSocketDisconnect:
        logger.info(f"Voice chat disconnected for user {user_id} in room {room_id}")
    except Exception as e:
        logger.error(f"Error in voice chat for user {user_id} in room {room_id}: {e}")
    finally:
        # Cleanup session
        await voice_manager.end_session(session_id)


@router.get("/voice/sessions")
async def get_active_voice_sessions(
    current_user: User = Depends(get_current_user)
):
    """Get active voice chat sessions"""
    sessions = voice_manager.get_active_sessions()
    return {"active_sessions": sessions}


@router.post("/voice/sessions/{session_id}/end")
async def end_voice_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Manually end a voice chat session"""
    await voice_manager.end_session(session_id)
    return {"message": "Voice session ended successfully"}