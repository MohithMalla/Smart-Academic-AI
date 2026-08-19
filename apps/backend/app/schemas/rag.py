from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.conversation import MessageRole


class RAGQueryFilters(BaseModel):
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    document_id: Optional[UUID] = None


class RAGQueryRequest(BaseModel):
    course_id: UUID
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: Optional[RAGQueryFilters] = None


class RAGCitation(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: Optional[int]
    rrf_score: float


class RAGQueryResponse(BaseModel):
    answer: str
    citations: List[RAGCitation]
    retrieval_metadata: Dict[str, Any]


class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    course_id: Optional[UUID] = None


class ConversationResponse(BaseModel):
    id: UUID
    institution_id: UUID
    user_id: UUID
    course_id: Optional[UUID]
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
