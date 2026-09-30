"""Audit log model for security tracking."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class AuditLog(Base):
    """Append-only security audit record tracking access, verification, and critical mutations."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_action_at", "action", "at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_user_id])
