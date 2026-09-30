"""Responder profile, skill, and credential models."""
from datetime import datetime, date, timezone
from typing import Optional
import uuid
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Date,
    Integer,
    Float,
    Text,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ResponderProfile(Base):
    """Volunteer responder profile, readiness status, location, and performance metrics."""
    __tablename__ = "responder_profiles"
    __table_args__ = (
        Index("ix_responder_readiness_loc", "readiness", "last_lat", "last_lng"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    readiness: Mapped[str] = mapped_column(String(32), default="off_duty", nullable=False)
    service_radius_m: Mapped[int] = mapped_column(Integer, default=3000, nullable=False)
    last_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_location_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pinned_location: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acceptance_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    responses_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cooldown_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="responder_profile")


class ResponderSkill(Base):
    """Qualified skills held by a responder with validated proficiency level."""
    __tablename__ = "responder_skills"
    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 3", name="ck_responder_skills_level"),
    )

    responder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    responder: Mapped["User"] = relationship("User", back_populates="skills")


class ResponderCredential(Base):
    """Formal qualification or certificate metadata reviewed by an authority."""
    __tablename__ = "responder_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    responder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_type: Mapped[str] = mapped_column(String(64), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_no: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    responder: Mapped["User"] = relationship(
        "User", back_populates="credentials", foreign_keys=[responder_id]
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by]
    )
