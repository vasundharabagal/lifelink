"""Security audit logging test suite (AUTH-05, D-34, D-35, D-36).

Verifies:
1. Anonymized salted HMAC-SHA256 IP hashing.
2. Immediate persistence in dedicated transaction surviving caller rollback.
3. Login audit events recorded on both success and failure.
4. Auditing of sensitive medical data and exact location reads.
"""
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import get_db, SessionLocal
from app.core.security import hash_password
from app.models.user import User, MedicalProfile
from app.models.audit import AuditLog
from app.models.emergency import Emergency, DispatchOffer
from app.domain.enums import UserRole, OfferStatus, TargetKind, EmergencyStatus, Priority, EmergencyType
from app.services.audit import anonymize_ip, log_security_event
from app.services.authz import assert_can_view_medical, assert_can_view_exact_location


def test_audit_ip_hashing():
    """Verify IP addresses are anonymized to 64-character hex strings (AUTH-05, D-35)."""
    raw_ip = "192.168.1.105"
    hashed = anonymize_ip(raw_ip)

    assert isinstance(hashed, str)
    assert len(hashed) == 64
    assert hashed != raw_ip

    # Determinism: same IP produces identical hash
    assert anonymize_ip(raw_ip) == hashed

    # Different IP produces different hash
    assert anonymize_ip("192.168.1.106") != hashed

    # Empty / None fallback produces consistent hash
    assert len(anonymize_ip(None)) == 64


def test_audit_persistence_on_abort():
    """Verify audit log survives caller transaction rollback (AUTH-05, D-34)."""
    test_id = f"test_rollback_{uuid.uuid4().hex[:8]}"

    # Caller opens a transaction and then intentionally rolls back
    session = SessionLocal()
    try:
        user = User(
            email=f"{test_id}@example.com",
            password_hash="dummy",
            full_name="Rollback Test",
            role="citizen",
            is_active=True,
        )
        session.add(user)

        # Record audit log in dedicated connection
        log_entry = log_security_event(
            action="test_action",
            resource_type="test_resource",
            resource_id=test_id,
            outcome="deny",
            actor_role="anonymous",
            client_ip="10.0.0.1",
        )

        # Roll back caller session
        session.rollback()
    finally:
        session.close()

    # Query with a fresh session: audit log MUST still exist in database
    verify_session = SessionLocal()
    try:
        saved_log = (
            verify_session.query(AuditLog)
            .filter(AuditLog.resource_id == test_id)
            .first()
        )
        assert saved_log is not None
        assert saved_log.action == "test_action"
        assert saved_log.outcome == "deny"

        # Verify user was indeed rolled back
        saved_user = (
            verify_session.query(User)
            .filter(User.email == f"{test_id}@example.com")
            .first()
        )
        assert saved_user is None
    finally:
        verify_session.close()


def test_audit_login_events(client, db_session):
    """Verify login success and failure both generate audit log entries (AUTH-05)."""
    email = f"audit_login_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "ValidPassword123!"
    user = User(
        email=email,
        password_hash=hash_password(pwd),
        full_name="Audit Login User",
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # 1. Failed login attempt (wrong password)
    res_fail = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert res_fail.status_code == 401

    # Check for DENY audit log
    fail_log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "auth_login",
            AuditLog.resource_id == email,
            AuditLog.outcome == "deny",
        )
        .first()
    )
    assert fail_log is not None

    # 2. Successful login attempt
    res_success = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert res_success.status_code == 200

    # Check for ALLOW audit log
    success_log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "auth_login",
            AuditLog.resource_id == email,
            AuditLog.outcome == "allow",
        )
        .first()
    )
    assert success_log is not None


def test_audit_sensitive_data_reads(db_session):
    """Verify reading medical profile or exact location creates audit record (AUTH-05, D-36)."""
    session_id = uuid.uuid4()

    patient = User(
        email=f"patient_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="pwd",
        full_name="Patient User",
        role="citizen",
        demo_session_id=session_id,
        is_active=True,
    )
    responder = User(
        email=f"resp_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="pwd",
        full_name="Accepted Responder",
        role="responder",
        demo_session_id=session_id,
        is_active=True,
    )
    db_session.add_all([patient, responder])
    db_session.flush()

    emergency = Emergency(
        patient_user_id=patient.id,
        reported_by_user_id=patient.id,
        idempotency_key=f"idem_{uuid.uuid4().hex}",
        status=EmergencyStatus.IN_PROGRESS.value,
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.CHEST_PAIN.value,
        triage={},
        lat=18.5204,
        lng=73.8567,
        consent_share_medical=True,
        demo_session_id=session_id,
    )
    db_session.add(emergency)
    db_session.flush()

    # Create accepted offer for responder
    offer = DispatchOffer(
        emergency_id=emergency.id,
        track="community",
        target_kind=TargetKind.RESPONDER.value,
        responder_id=responder.id,
        rank=1,
        status=OfferStatus.ACCEPTED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    med_profile = MedicalProfile(
        user_id=patient.id,
        blood_group="A+",
        allergies=["peanuts"],
        conditions=[],
    )
    db_session.add_all([offer, med_profile])
    db_session.commit()

    # 1. Read medical profile as accepted responder
    can_view_med = assert_can_view_medical(responder, emergency, med_profile, db_session)
    assert can_view_med is True

    # Verify audit log was recorded
    med_audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "sensitive_read_medical_profile",
            AuditLog.resource_id == str(emergency.id),
            AuditLog.actor_user_id == responder.id,
        )
        .first()
    )
    assert med_audit is not None
    assert med_audit.actor_role == "responder"

    # 2. Read exact location as accepted responder
    can_view_loc = assert_can_view_exact_location(responder, emergency, db_session)
    assert can_view_loc is True

    loc_audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "sensitive_read_exact_location",
            AuditLog.resource_id == str(emergency.id),
            AuditLog.actor_user_id == responder.id,
        )
        .first()
    )
    assert loc_audit is not None
