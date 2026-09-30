"""Security audit logging service (AUTH-05, D-34, D-35, D-36).

Provides:
- Salted HMAC-SHA256 client IP anonymization.
- Immediate committed audit logs surviving transaction rollbacks.
- Auditing for login attempts, authorization denials, and sensitive data access.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import logging
from typing import Optional, Dict, Any
import uuid
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.clock import Clock, get_clock
from app.domain.enums import AuditOutcome
from app.models.audit import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


def anonymize_ip(ip: Optional[str]) -> str:
    """Anonymize IP address using salted HMAC-SHA256 (AUTH-05, D-35).
    
    Produces a deterministic, irreversible 64-character hex string.
    """
    clean_ip = (ip or "0.0.0.0").strip()
    return hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        clean_ip.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def extract_client_ip(request: Optional[Request]) -> str:
    """Safely extract client IP from X-Forwarded-For or request.client."""
    if not request:
        return "127.0.0.1"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def log_security_event(
    action: str,
    resource_type: str,
    resource_id: str,
    outcome: str,
    actor_user_id: Optional[uuid.UUID] = None,
    actor_role: str = "anonymous",
    client_ip: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    at: Optional[datetime] = None,
    db: Optional[Session] = None,
) -> AuditLog:
    """Record an immutable security event to audit_logs (AUTH-05, D-34).
    
    If no session is passed, commits in an isolated dedicated transaction
    using SessionLocal() so the audit entry survives caller aborts/rollbacks.
    """
    ip_hash = anonymize_ip(client_ip)
    timestamp = at or get_clock().now()

    # Use provided session or create isolated dedicated transaction
    owns_session = db is None
    session = db if db is not None else SessionLocal()

    try:
        log_entry = AuditLog(
            at=timestamp,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            outcome=outcome,
            ip_hash=ip_hash,
            meta=meta or {},
        )
        session.add(log_entry)
        session.commit()
        session.refresh(log_entry)
        return log_entry
    except Exception as e:
        session.rollback()
        logger.warning(f"Failed to record audit log: {e}")
        return AuditLog(
            at=timestamp,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            outcome=outcome,
            ip_hash=ip_hash,
            meta=meta or {},
        )
    finally:
        if owns_session:
            session.close()


def log_login_attempt(
    email: str,
    success: bool,
    user: Optional[User] = None,
    request: Optional[Request] = None,
    clock: Optional[Clock] = None,
    db: Optional[Session] = None,
) -> AuditLog:
    """Audit user login attempt."""
    client_ip = extract_client_ip(request)
    timestamp = (
        clock.now(user.demo_session_id if user else None, db)
        if clock
        else get_clock().now()
    )
    outcome = AuditOutcome.ALLOW.value if success else AuditOutcome.DENY.value

    return log_security_event(
        action="auth_login",
        resource_type="user",
        resource_id=email,
        outcome=outcome,
        actor_user_id=user.id if user else None,
        actor_role=user.role if user else "anonymous",
        client_ip=client_ip,
        meta={"auth_method": "password"},
        at=timestamp,
        db=db,
    )


def log_authz_denial(
    actor: Optional[User],
    resource_type: str,
    resource_id: str,
    request: Optional[Request] = None,
    clock: Optional[Clock] = None,
    meta: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> AuditLog:
    """Audit authorization failure or denial (D-34)."""
    client_ip = extract_client_ip(request)
    timestamp = (
        clock.now(actor.demo_session_id if actor else None, db)
        if clock
        else get_clock().now()
    )

    return log_security_event(
        action=f"authz_denial_{resource_type}",
        resource_type=resource_type,
        resource_id=str(resource_id),
        outcome=AuditOutcome.DENY.value,
        actor_user_id=actor.id if actor else None,
        actor_role=actor.role if actor else "anonymous",
        client_ip=client_ip,
        meta=meta or {},
        at=timestamp,
        db=db,
    )


def log_sensitive_data_read(
    actor: User,
    emergency_id: uuid.UUID,
    data_type: str,
    request: Optional[Request] = None,
    clock: Optional[Clock] = None,
    meta: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> AuditLog:
    """Audit read access to sensitive coordinates or medical profile (AUTH-05, D-36)."""
    client_ip = extract_client_ip(request)
    timestamp = (
        clock.now(actor.demo_session_id, db)
        if clock
        else get_clock().now()
    )

    event_meta = {"data_type": data_type}
    if meta:
        event_meta.update(meta)

    return log_security_event(
        action=f"sensitive_read_{data_type}",
        resource_type="emergency",
        resource_id=str(emergency_id),
        outcome=AuditOutcome.ALLOW.value,
        actor_user_id=actor.id,
        actor_role=actor.role,
        client_ip=client_ip,
        meta=event_meta,
        at=timestamp,
        db=db,
    )
