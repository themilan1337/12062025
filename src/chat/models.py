from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChatRoomBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = True


class ChatRoomCreate(ChatRoomBase):
    pass


class ChatRoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class ChatRoom(ChatRoomBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    content: str
    message_type: str = "text"


class MessageCreate(MessageBase):
    room_id: int


class Message(MessageBase):
    id: int
    room_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatParticipantBase(BaseModel):
    room_id: int
    user_id: int
    is_admin: bool = False


class ChatParticipantCreate(ChatParticipantBase):
    pass


class ChatParticipant(ChatParticipantBase):
    id: int
    joined_at: datetime

    class Config:
        from_attributes = True


class WebSocketMessage(BaseModel):
    type: str
    content: Optional[str] = None
    room_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    timestamp: Optional[datetime] = None


class RoomWithMessages(ChatRoom):
    messages: List[Message] = []
    participants: List[ChatParticipant] = []
