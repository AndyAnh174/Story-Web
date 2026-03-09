from pydantic import BaseModel
from datetime import datetime


class ProjectCreate(BaseModel):
    title: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    id: str
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
