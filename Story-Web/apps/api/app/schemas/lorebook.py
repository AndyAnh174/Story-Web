from pydantic import BaseModel
from datetime import datetime
from typing import Literal


LorebookCategory = Literal["Skill", "Character", "Rule", "Location", "Item", "Other"]


class LorebookCreate(BaseModel):
    keyword: str
    category: LorebookCategory = "Rule"
    description: str


class LorebookUpdate(BaseModel):
    keyword: str | None = None
    category: LorebookCategory | None = None
    description: str | None = None


class LorebookResponse(BaseModel):
    id: str
    project_id: str
    keyword: str
    category: str
    description: str
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
