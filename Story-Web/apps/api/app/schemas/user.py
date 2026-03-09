from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    clerk_id: str
    email: EmailStr
    name: str | None = None


class UserResponse(BaseModel):
    id: str
    clerk_id: str
    email: str
    name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
