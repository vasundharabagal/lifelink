"""Demo session isolation model."""
from datetime import datetime, timezone
from typing import Dict, Any
import uuid
from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class DemoSession(Base):
    """Isolated tenant session for judges and demo scenario runs."""
    __tablename__ = "demo_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    clock_offset_s: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    scenario: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
