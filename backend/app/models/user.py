"""User and MedicalProfile models."""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class User(Base):
    """User account entity across citizen, responder, operator, and authority roles."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    demo_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    medical_profile: Mapped[Optional["MedicalProfile"]] = relationship(
        "MedicalProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    responder_profile: Mapped[Optional["ResponderProfile"]] = relationship(
        "ResponderProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    credentials: Mapped[List["ResponderCredential"]] = relationship(
        "ResponderCredential", back_populates="responder", foreign_keys="ResponderCredential.responder_id"
    )
    skills: Mapped[List["ResponderSkill"]] = relationship(
        "ResponderSkill", back_populates="responder", cascade="all, delete-orphan"
    )


class MedicalProfile(Base):
    """Optional personal medical information with explicit emergency sharing consent."""
    __tablename__ = "medical_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blood_group: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    allergies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contacts: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    share_during_emergency: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="medical_profile")
