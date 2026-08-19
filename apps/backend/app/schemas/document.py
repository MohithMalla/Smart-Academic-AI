from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentStatus


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    status: DocumentStatus
    message: str = "Document uploaded successfully and queued for processing."


class DocumentResponse(BaseModel):
    id: UUID
    institution_id: UUID
    course_id: UUID
    uploaded_by: UUID
    filename: str
    original_filename: str
    mime_type: str
    file_size: int
    status: DocumentStatus
    page_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
