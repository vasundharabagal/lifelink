"""Emergency, emergency events, and dispatch offers models."""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Integer,
    Float,
    Text,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Emergency(Base):
    """Core emergency incident entity tracking dual-track dispatch and clinical lifecycle."""
    __tablename__ = "emergencies"
    __table_args__ = (
        Index("ix_emergencies_status_demo", "status", "demo_session_id"),
        CheckConstraint("lat BETWEEN -90 AND 90", name="ck_emergencies_lat"),
        CheckConstraint("lng BETWEEN -180 AND 180", name="ck_emergencies_lng"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False)
    community_track: Mapped[str] = mapped_column(String(32), default="NOT_STARTED", nullable=False)
    professional_track: Mapped[str] = mapped_column(String(32), default="NOT_STARTED", nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    emergency_type: Mapped[str] = mapped_column(String(64), nullable=False)
    triage: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dispatch_plan: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    location_accuracy_m: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    location_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    patient_is_reporter: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    consent_share_medical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    next_event_seq: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    handover_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    close_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    demo_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_user_id])
    reporter: Mapped["User"] = relationship("User", foreign_keys=[reported_by_user_id])
    events: Mapped[List["EmergencyEvent"]] = relationship(
        "EmergencyEvent", back_populates="emergency", cascade="all, delete-orphan", order_by="EmergencyEvent.seq"
    )
    offers: Mapped[List["DispatchOffer"]] = relationship(
        "DispatchOffer", back_populates="emergency", cascade="all, delete-orphan"
    )


class EmergencyEvent(Base):
    """Append-only chronological timeline event for an emergency."""
    __tablename__ = "emergency_events"
    __table_args__ = (
        UniqueConstraint("emergency_id", "seq", name="uq_events_emergency_seq"),
        Index("ix_events_emergency_seq", "emergency_id", "seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    emergency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emergencies.id", ondelete="CASCADE"),
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    visible_to: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    emergency: Mapped["Emergency"] = relationship("Emergency", back_populates="events")
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_user_id])


class DispatchOffer(Base):
    """Polymorphic dispatch offer to a community responder or ambulance unit."""
    __tablename__ = "dispatch_offers"
    __table_args__ = (
        CheckConstraint(
            "((target_kind = 'responder' AND responder_id IS NOT NULL AND ambulance_id IS NULL) OR "
            "(target_kind = 'ambulance' AND ambulance_id IS NOT NULL AND responder_id IS NULL))",
            name="ck_offer_target_kind",
        ),
        Index("ix_offers_status_expiry", "status", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    emergency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emergencies.id", ondelete="CASCADE"),
        nullable=False,
    )
    track: Mapped[str] = mapped_column(String(32), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    responder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ambulance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ambulance_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OFFERED", nullable=False)
    offered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    arrived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decline_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    eta_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    sim_start_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sim_start_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sim_travel_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actions_reported: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    emergency: Mapped["Emergency"] = relationship("Emergency", back_populates="offers")
    responder: Mapped[Optional["User"]] = relationship("User", foreign_keys=[responder_id])
    ambulance: Mapped[Optional["AmbulanceUnit"]] = relationship(
        "AmbulanceUnit", foreign_keys=[ambulance_id]
    )
