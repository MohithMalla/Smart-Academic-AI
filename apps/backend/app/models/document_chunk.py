import uuid
from typing import Any, Dict, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chapter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 768-dim vector embedding (pgvector Vector in Postgres, fallback to JSON in SQLite tests)
    embedding: Mapped[Optional[Any]] = mapped_column(
        Vector(768).with_variant(JSON, "sqlite"),
        nullable=True
    )
    
    # JSONB in Postgres, fallback to JSON in SQLite tests
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default={},
        nullable=True
    )

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_institution_course", "institution_id", "course_id"),
        Index("idx_chunks_subject_chapter_topic", "institution_id", "subject", "chapter", "topic"),
    )
