"""Route enumeration and RBAC permission boundary test suite (AUTH-03).

Verifies:
1. 100% of non-public API endpoints require authentication (deny-by-default).
2. Role-based access control enforces strict role boundaries (403 FORBIDDEN on violation).
3. Unauthenticated calls receive 401 UNAUTHENTICATED.
"""
import uuid
import pytest
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import get_db
from app.core.security import create_access_token, hash_password
from app.api.deps import (
    get_current_user,
    require_role,
    require_citizen,
    require_responder,
    require_ambulance,
    require_authority,
)
from app.domain.enums import UserRole
from app.models.user import User


# Public endpoints allowed without authentication
PUBLIC_ROUTES = {
    "/",
    "/api/v1/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/openapi.json",
}


def _has_auth_guard(dependant) -> bool:
    """Recursively inspect FastAPI Dependant tree for get_current_user or require_role."""
    if dependant.call == get_current_user:
        return True
    if getattr(dependant.call, "__name__", "") == "_role_dependency":
        return True
    for sub in dependant.dependencies:
        if _has_auth_guard(sub):
            return True
    return False


def test_route_enumeration_deny_by_default():
    """Verify that all non-whitelisted routes require authentication (AUTH-03)."""
    unprotected_routes = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        if route.path in PUBLIC_ROUTES:
            continue

        # Check route-level dependencies and endpoint parameter dependants
        route_has_auth = _has_auth_guard(route.dependant)
        if not route_has_auth:
            unprotected_routes.append(f"{route.methods} {route.path}")

    assert not unprotected_routes, (
        f"Found unprotected non-public routes violating deny-by-default: {unprotected_routes}"
    )


# Attach a temporary router to test role boundaries
rbac_test_router = APIRouter(prefix="/api/v1/test-rbac", tags=["test-rbac"])


@rbac_test_router.get("/citizen-only")
def citizen_endpoint(user: User = Depends(require_citizen)):
    return {"message": "ok", "user": user.email}


@rbac_test_router.get("/responder-only")
def responder_endpoint(user: User = Depends(require_responder)):
    return {"message": "ok", "user": user.email}


@rbac_test_router.get("/ambulance-only")
def ambulance_endpoint(user: User = Depends(require_ambulance)):
    return {"message": "ok", "user": user.email}


@rbac_test_router.get("/authority-only")
def authority_endpoint(user: User = Depends(require_authority)):
    return {"message": "ok", "user": user.email}


@rbac_test_router.get("/multi-role")
def multi_role_endpoint(
    user: User = Depends(require_role(UserRole.RESPONDER, UserRole.AUTHORITY))
):
    return {"message": "ok", "user": user.email}


app.include_router(rbac_test_router)


@pytest.fixture
def rbac_client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_rbac_unauthenticated_rejected(rbac_client):
    """Verify unauthenticated requests to protected endpoints return 401."""
    res = rbac_client.get("/api/v1/test-rbac/citizen-only")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_rbac_role_boundaries_matrix(rbac_client, db_session):
    """Verify strict role-based access control matrix (AUTH-03)."""
    # Create test users for each role
    users = {}
    tokens = {}
    for role_enum in (
        UserRole.CITIZEN,
        UserRole.RESPONDER,
        UserRole.AMBULANCE_OPERATOR,
        UserRole.AUTHORITY,
    ):
        email = f"user_{role_enum.value}_{uuid.uuid4().hex[:6]}@example.com"
        user = User(
            email=email,
            password_hash=hash_password("Pass12345678!"),
            full_name=f"Test {role_enum.value}",
            role=role_enum.value,
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()
        users[role_enum.value] = user
        tokens[role_enum.value] = create_access_token(user_id=user.id, role=user.role)

    # 1. Citizen tests
    res = rbac_client.get(
        "/api/v1/test-rbac/citizen-only",
        headers={"Authorization": f"Bearer {tokens['citizen']}"},
    )
    assert res.status_code == 200

    res = rbac_client.get(
        "/api/v1/test-rbac/responder-only",
        headers={"Authorization": f"Bearer {tokens['citizen']}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 2. Responder tests
    res = rbac_client.get(
        "/api/v1/test-rbac/responder-only",
        headers={"Authorization": f"Bearer {tokens['responder']}"},
    )
    assert res.status_code == 200

    res = rbac_client.get(
        "/api/v1/test-rbac/authority-only",
        headers={"Authorization": f"Bearer {tokens['responder']}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 3. Ambulance operator tests
    res = rbac_client.get(
        "/api/v1/test-rbac/ambulance-only",
        headers={"Authorization": f"Bearer {tokens['ambulance_operator']}"},
    )
    assert res.status_code == 200

    res = rbac_client.get(
        "/api/v1/test-rbac/citizen-only",
        headers={"Authorization": f"Bearer {tokens['ambulance_operator']}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 4. Multi-role endpoint tests
    res = rbac_client.get(
        "/api/v1/test-rbac/multi-role",
        headers={"Authorization": f"Bearer {tokens['responder']}"},
    )
    assert res.status_code == 200

    res = rbac_client.get(
        "/api/v1/test-rbac/multi-role",
        headers={"Authorization": f"Bearer {tokens['authority']}"},
    )
    assert res.status_code == 200

    res = rbac_client.get(
        "/api/v1/test-rbac/multi-role",
        headers={"Authorization": f"Bearer {tokens['citizen']}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
