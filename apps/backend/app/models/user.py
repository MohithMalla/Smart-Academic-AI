import enum
import uuid
from typing import Optional
from sqlalchemy import Enum as SQLEnum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Role(str, enum.Enum):
    INSTITUTION_ADMIN = "INSTITUTION_ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


class User(Base):
    __tablename__ = "users"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    role: Mapped[Role] = mapped_column(
        SQLEnum(Role, name="user_role_enum", native_enum=False),
        nullable=False,
        default=Role.STUDENT
    )
    
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    institution = relationship("Institution", back_populates="users")

    __table_args__ = (
        UniqueConstraint("institution_id", "email", name="uq_user_institution_email"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
