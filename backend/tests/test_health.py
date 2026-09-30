import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.core.db import get_db
from app.core.config import Settings


client = TestClient(app)


def test_health_endpoint_schema():
    """Verify GET /api/v1/health returns 200 and conformant response schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "db" in data
    assert data["version"] == "1.0"
    assert "demo_mode" in data
    assert "timestamp" in data
    assert "environment" in data


def test_health_endpoint_db_success():
    """Verify GET /api/v1/health reports db: ok when SELECT 1 succeeds."""
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 1

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_db_failure_resilience():
    """Verify GET /api/v1/health handles database failure gracefully without crashing (T-00-01)."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = OperationalError("connection refused", {}, None)

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "error"
    finally:
        app.dependency_overrides.clear()


def test_database_url_normalization():
    """Verify database connection URL dialect normalization."""
    # postgres:// normalized to postgresql+psycopg2://
    s1 = Settings(DATABASE_URL="postgres://user:pass@localhost:5432/db")
    assert s1.DATABASE_URL.startswith("postgresql+psycopg2://")

    # postgresql:// without driver normalized to postgresql+psycopg2://
    s2 = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert s2.DATABASE_URL.startswith("postgresql+psycopg2://")

    # already explicit dialect preserved
    s3 = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db")
    assert s3.DATABASE_URL.startswith("postgresql+asyncpg://")

    # SQLite URL preserved
    s4 = Settings(DATABASE_URL="sqlite:///./test.db")
    assert s4.DATABASE_URL == "sqlite:///./test.db"
