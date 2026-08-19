from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None


class CourseResponse(BaseModel):
    id: UUID
    institution_id: UUID
    code: str
    name: str
    description: Optional[str]
    created_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
