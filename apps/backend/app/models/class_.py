import uuid
from typing import List
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Class(Base):
    __tablename__ = "classes"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    academic_term: Mapped[str] = mapped_column(String(50), nullable=False)

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Relationships
    course = relationship("Course", back_populates="classes")
    enrollments: Mapped[List["Enrollment"]] = relationship("Enrollment", back_populates="class_", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("institution_id", "course_id", "name", "academic_term", name="uq_class_institution_course_name_term"),
        Index("idx_classes_institution_course", "institution_id", "course_id"),
    )
