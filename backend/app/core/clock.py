"""Injectable deterministic Clock service supporting virtual time offsets."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.demo import DemoSession


class Clock:
    """Injectable time provider supporting real-time and virtual demo session offsets (DATA-04)."""

    def now(
        self,
        demo_session_id: Optional[UUID] = None,
        db: Optional[Session] = None,
    ) -> datetime:
        """Return the current timezone-aware UTC datetime, optionally offset by a demo session.
        
        If demo_session_id and db are provided, the session's clock_offset_s is added
        to current UTC time. If not found or not provided, real UTC time is returned.
        """
        current_utc = datetime.now(timezone.utc)
        if demo_session_id is None or db is None:
            return current_utc

        demo_session = db.query(DemoSession).filter(DemoSession.id == demo_session_id).first()
        if demo_session and demo_session.clock_offset_s:
            return current_utc + timedelta(seconds=demo_session.clock_offset_s)

        return current_utc

    def advance(
        self,
        demo_session_id: UUID,
        seconds: int,
        db: Session,
    ) -> datetime:
        """Advance the virtual clock for a demo session by the specified seconds."""
        demo_session = (
            db.query(DemoSession)
            .filter(DemoSession.id == demo_session_id)
            .with_for_update()
            .first()
        )
        if not demo_session:
            raise ValueError(f"Demo session not found: {demo_session_id}")

        demo_session.clock_offset_s += seconds
        db.commit()
        return self.now(demo_session_id, db)

    def reset(
        self,
        demo_session_id: UUID,
        db: Session,
    ) -> datetime:
        """Reset the virtual clock offset for a demo session back to zero."""
        demo_session = (
            db.query(DemoSession)
            .filter(DemoSession.id == demo_session_id)
            .with_for_update()
            .first()
        )
        if not demo_session:
            raise ValueError(f"Demo session not found: {demo_session_id}")

        demo_session.clock_offset_s = 0
        db.commit()
        return self.now(demo_session_id, db)


_clock_instance = Clock()


def get_clock() -> Clock:
    """FastAPI dependency yielding the Clock singleton."""
    return _clock_instance
