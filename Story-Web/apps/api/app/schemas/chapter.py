from pydantic import BaseModel, Field
from datetime import datetime


class ChapterCreate(BaseModel):
    title: str = Field(max_length=200)
    content: str = Field(max_length=50000)
    order_index: int = 1


class ChapterUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=50000)
    order_index: int | None = None


class ChapterResponse(BaseModel):
    id: str
    project_id: str
    title: str
    content: str
    order_index: int
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
