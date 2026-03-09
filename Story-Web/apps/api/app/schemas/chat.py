from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class ChatCreate(BaseModel):
    title: str = "Cuộc trò chuyện mới"


class ChatResponse(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    role: Literal["user", "ai", "system"]
    content: str


class ChatMessageResponse(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StreamChatRequest(BaseModel):
    content: str                              # Tin nhắn từ user
    custom_system_prompt: str | None = None   # Hướng dẫn thêm từ tác giả (gắn vào cuối system prompt)
