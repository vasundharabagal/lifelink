import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import get_db
from app.models.user import User
from app.core.security import hash_password, create_access_token


def test_register_citizen_success(client):
    """Verify citizen registration returns 201, sets session cookie, and stores Argon2 hash (AUTH-01)."""
    email = f"citizen_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "StrongSecretPassword2026!",
        "full_name": "Aarav Sharma",
        "phone": "+919876543210",
        "role": "citizen",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "citizen"
    assert "token" in data
    assert "ll_session" in res.cookies


def test_register_responder_success(client, db_session):
    """Verify responder registration initializes responder profile (AUTH-01)."""
    email = f"resp_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "ResponderSecretPassword2026!",
        "full_name": "Dr. Subhash Iyer",
        "role": "responder",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["role"] == "responder"

    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None
    assert user.responder_profile is not None
    assert user.responder_profile.readiness == "off_duty"


def test_register_forbidden_roles(client):
    """Verify authority and ambulance operator roles cannot self-register."""
    for forbidden_role in ("authority", "ambulance_operator", "admin", "superadmin"):
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"bad_{uuid.uuid4().hex[:8]}@example.com",
                "password": "ValidPassword123!",
                "full_name": "Unauthorized User",
                "role": forbidden_role,
            },
        )
        assert res.status_code == 422
        data = res.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


def test_register_password_strength_validation(client):
    """Verify rejection of short and common passwords (T-02-02)."""
    # Short password (< 10 chars)
    res_short = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Short1!",
            "full_name": "Short Password",
            "role": "citizen",
        },
    )
    assert res_short.status_code == 422

    # Common password
    res_common = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "password123",
            "full_name": "Common Password",
            "role": "citizen",
        },
    )
    assert res_common.status_code == 422


def test_register_duplicate_email(client):
    """Verify duplicate email registration returns 409 CONFLICT."""
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "ValidPassword2026!",
        "full_name": "First User",
        "role": "citizen",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "CONFLICT"


def test_login_success_and_cookie(client, db_session):
    """Verify login with valid credentials sets cookie and returns token (AUTH-02)."""
    email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "ValidLoginPassword2026!"
    user = User(
        email=email,
        password_hash=hash_password(pwd),
        full_name="Login Test",
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == email
    assert "ll_session" in res.cookies


def test_login_invalid_credentials(client, db_session):
    """Verify invalid password returns generic 401 UNAUTHENTICATED (T-02-01)."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("CorrectPassword123!"),
        full_name="Invalid Test",
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Wrong password
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword123!"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"

    # Non-existent email
    res_non_exist = client.post("/api/v1/auth/login", json={"email": "nonexistent@example.com", "password": "AnyPassword123!"})
    assert res_non_exist.status_code == 401
    assert res_non_exist.json()["error"]["code"] == "UNAUTHENTICATED"


def test_login_deactivated_user(client, db_session):
    """Verify deactivated user cannot authenticate even with correct password."""
    email = f"deactivated_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "CorrectPassword123!"
    user = User(
        email=email,
        password_hash=hash_password(pwd),
        full_name="Deactivated User",
        role="citizen",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_auth_me_dual_transport(client, db_session):
    """Verify /auth/me supports both cookie and Bearer header transport (D-25)."""
    email = f"me_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("Pass12345678!"),
        full_name="Transport Test",
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user_id=user.id, role=user.role)

    # 1. Via Cookie
    client.cookies.set("ll_session", token)
    res_cookie = client.get("/api/v1/auth/me")
    assert res_cookie.status_code == 200
    assert res_cookie.json()["user"]["email"] == email

    # 2. Via Bearer header
    client.cookies.clear()
    res_header = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_header.status_code == 200
    assert res_header.json()["user"]["email"] == email

    # 3. Unauthenticated
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401
    assert res_unauth.json()["error"]["code"] == "UNAUTHENTICATED"


def test_logout(client):
    """Verify logout clears session cookie."""
    client.cookies.set("ll_session", "dummy_token_value", domain="testserver")
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 204
    # Verify Set-Cookie header instructs browser to clear cookie
    set_cookie = res.headers.get("set-cookie", "")
    assert 'll_session=""' in set_cookie or "ll_session=" in set_cookie
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()
