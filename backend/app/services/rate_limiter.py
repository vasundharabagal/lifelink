"""Database-derived serverless rate limiting service (AUTH-06, D-31, D-32, D-33).

Calculates rate limits dynamically from persistent PostgreSQL audit_logs
and emergencies tables without relying on in-memory or Redis caches.
All time windows evaluate relative to Clock.now(demo_session_id).
"""
from datetime import timedelta
from typing import Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.domain.enums import AuditOutcome
from app.models.audit import AuditLog
from app.models.emergency import Emergency
from app.models.responder import ResponderProfile


def check_login_rate_limit(
    email: str,
    db: Session,
    clock: Clock,
    demo_session_id: Optional[uuid.UUID] = None,
) -> None:
    """Enforce login rate limiting: 5 failed attempts per 15 minutes (AUTH-06, D-31).
    
    Locks the account when 5 or more failed attempts exist within the 15-minute
    rolling window relative to clock.now(demo_session_id).
    Returns HTTP 429 with Retry-After header (D-32).
    """
    now_dt = clock.now(demo_session_id, db)
    cutoff = now_dt - timedelta(minutes=15)

    failed_attempts = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "auth_login",
            AuditLog.outcome == AuditOutcome.DENY.value,
            AuditLog.resource_id == email.strip().lower(),
            AuditLog.at >= cutoff,
        )
        .order_by(AuditLog.at.asc())
        .all()
    )

    if len(failed_attempts) >= 5:
        oldest = failed_attempts[0]
        elapsed_s = (now_dt - oldest.at).total_seconds()
        retry_after = max(1, int(15 * 60 - elapsed_s))

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": f"Too many failed login attempts. Account locked. Try again in {retry_after} seconds.",
                    "retry_after_s": retry_after,
                }
            },
            headers={"Retry-After": str(retry_after)},
        )


def check_sos_rate_limit(
    user_id: uuid.UUID,
    db: Session,
    clock: Clock,
    demo_session_id: Optional[uuid.UUID] = None,
) -> None:
    """Enforce SOS flood limit: maximum 3 emergency incidents per hour (AUTH-06).
    
    Prevents emergency dispatch exhaustion and denial-of-service.
    """
    now_dt = clock.now(demo_session_id, db)
    cutoff = now_dt - timedelta(hours=1)

    count = (
        db.query(Emergency)
        .filter(
            Emergency.reported_by_user_id == user_id,
            Emergency.created_at >= cutoff,
        )
        .count()
    )

    if count >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "SOS creation limit exceeded (maximum 3 per hour). Call 112 directly.",
                    "retry_after_s": 1800,
                }
            },
            headers={"Retry-After": "1800"},
        )


def check_location_rate_limit(
    responder_profile: ResponderProfile,
    clock: Clock,
    demo_session_id: Optional[uuid.UUID] = None,
    db: Optional[Session] = None,
) -> None:
    """Enforce responder location telemetry rate limit: maximum 1 per 5 seconds (AUTH-06)."""
    if responder_profile.last_location_at is not None:
        now_dt = clock.now(demo_session_id, db)
        elapsed = (now_dt - responder_profile.last_location_at).total_seconds()
        if elapsed < 5:
            retry_after = max(1, int(5 - elapsed))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Location telemetry rate limit exceeded (maximum 1 per 5s)",
                        "retry_after_s": retry_after,
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )
