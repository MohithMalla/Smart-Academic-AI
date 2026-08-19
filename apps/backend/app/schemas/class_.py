from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ClassCreate(BaseModel):
    course_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    academic_term: str = Field(..., min_length=1, max_length=50)
    teacher_id: UUID


class ClassResponse(BaseModel):
    id: UUID
    institution_id: UUID
    course_id: UUID
    name: str
    academic_term: str
    teacher_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
