"""Ambulance unit model."""
from typing import Optional
import uuid
from sqlalchemy import String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class AmbulanceUnit(Base):
    """Professional emergency vehicle unit tracked by dispatch."""
    __tablename__ = "ambulance_units"
    __table_args__ = (
        UniqueConstraint("callsign", "demo_session_id", name="uq_ambulance_callsign_session"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    operator_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    callsign: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit_type: Mapped[str] = mapped_column(String(32), default="basic", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    base_name: Mapped[str] = mapped_column(String(255), nullable=False)
    demo_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    operator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[operator_user_id])
