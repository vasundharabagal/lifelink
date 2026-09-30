"""Rate limiter verification test suite (AUTH-06, D-31, D-32, D-33).

Verifies:
1. DB-derived login rate limiting (5 failed attempts locks account).
2. HTTP 429 response structure with Retry-After header.
3. Clock time-travel awareness (unlocking account after 15m window).
4. SOS flood rate limiting (maximum 3 per hour).
5. Location telemetry rate limiting (maximum 1 per 5s).
"""
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.clock import get_clock
from app.core.db import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.demo import DemoSession
from app.models.emergency import Emergency
from app.models.responder import ResponderProfile
from app.domain.enums import UserRole, EmergencyStatus, Priority, EmergencyType
from app.services.rate_limiter import (
    check_login_rate_limit,
    check_sos_rate_limit,
    check_location_rate_limit,
)


def test_login_rate_limiting(client, db_session):
    """Verify 5 failed logins locks account and 6th attempt returns 429 (AUTH-06, D-31, D-32)."""
    email = f"brute_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "ValidSecretPassword1!"
    user = User(
        email=email,
        password_hash=hash_password(pwd),
        full_name="Brute Force Target",
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # 1. Five failed login attempts
    for attempt in range(1, 6):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHENTICATED"

    # 2. Sixth attempt must be rejected with 429 RATE_LIMITED
    res_locked = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert res_locked.status_code == 429
    data = res_locked.json()
    assert data["error"]["code"] == "RATE_LIMITED"
    assert "retry_after_s" in data["error"]
    assert "Retry-After" in res_locked.headers
    assert int(res_locked.headers["Retry-After"]) > 0

    # 3. Even correct password is blocked while locked
    res_correct_while_locked = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert res_correct_while_locked.status_code == 429


def test_rate_limiter_clock_awareness(client, db_session):
    """Verify account automatically unlocks when Clock advances past lockout window (D-33)."""
    session_id = uuid.uuid4()
    demo_session = DemoSession(
        id=session_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        clock_offset_s=0,
        scenario={},
        is_active=True,
    )
    email = f"timetravel_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "ValidSecretPassword1!"
    user = User(
        email=email,
        password_hash=hash_password(pwd),
        full_name="Time Traveler",
        role="citizen",
        demo_session_id=session_id,
        is_active=True,
    )
    db_session.add_all([demo_session, user])
    db_session.commit()

    # Trigger 5 failed logins to lock account
    for _ in range(5):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "BadPassword!"},
        )
        assert res.status_code == 401

    # Verify locked
    res_locked = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "BadPassword!"},
    )
    assert res_locked.status_code == 429

    # Advance clock by 16 minutes (960 seconds) past the 15-minute window
    clock = get_clock()
    clock.advance(session_id, 960, db_session)

    # Now login with correct password succeeds!
    res_unlocked = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert res_unlocked.status_code == 200
    assert res_unlocked.json()["user"]["email"] == email


def test_sos_rate_limiting(db_session):
    """Verify maximum 3 SOS emergency incidents per hour per user (AUTH-06)."""
    clock = get_clock()
    now_dt = clock.now()

    user = User(
        email=f"reporter_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="pwd",
        full_name="SOS Reporter",
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    # Create 3 emergencies in current hour (2 completed, 1 active to satisfy uq_emergencies_active_patient)
    for i in range(3):
        status_val = EmergencyStatus.COMPLETED.value if i < 2 else EmergencyStatus.DISPATCHING.value
        em = Emergency(
            patient_user_id=user.id,
            reported_by_user_id=user.id,
            idempotency_key=f"idem_sos_{i}_{uuid.uuid4().hex}",
            status=status_val,
            priority=Priority.P1_CRITICAL.value,
            emergency_type=EmergencyType.CHEST_PAIN.value,
            triage={},
            lat=18.5204,
            lng=73.8567,
            created_at=now_dt - timedelta(minutes=10 * (i + 1)),
        )
        db_session.add(em)
    db_session.commit()

    # 4th check should raise 429
    with pytest.raises(HTTPException) as exc_info:
        check_sos_rate_limit(user_id=user.id, db=db_session, clock=clock)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["error"]["code"] == "RATE_LIMITED"
    assert exc_info.value.headers["Retry-After"] == "1800"


def test_location_rate_limiting():
    """Verify location telemetry rate limiter throttles updates under 5 seconds."""
    clock = get_clock()
    now_dt = clock.now()

    # Profile updated 2 seconds ago
    profile = ResponderProfile(
        user_id=uuid.uuid4(),
        category="other",
        last_location_at=now_dt - timedelta(seconds=2),
    )

    with pytest.raises(HTTPException) as exc_info:
        check_location_rate_limit(profile, clock)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["error"]["code"] == "RATE_LIMITED"

    # Profile updated 6 seconds ago: allowed
    profile.last_location_at = now_dt - timedelta(seconds=6)
    check_location_rate_limit(profile, clock)
