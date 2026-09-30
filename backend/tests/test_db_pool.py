from sqlalchemy.pool import NullPool, QueuePool
from app.core import db as db_module
from app.core.config import settings


def test_db_pool_development():
    """Verify QueuePool is selected in development environment."""
    original_env = settings.APP_ENV
    original_url = settings.DATABASE_URL
    try:
        settings.APP_ENV = "development"
        settings.DATABASE_URL = "postgresql+psycopg2://user:pass@localhost:5432/db"
        engine = db_module.get_engine()
        assert isinstance(engine.pool, QueuePool), f"Expected QueuePool, got {type(engine.pool)}"
    finally:
        settings.APP_ENV = original_env
        settings.DATABASE_URL = original_url


def test_db_pool_production_serverless():
    """Verify NullPool is selected in production/preview environment (T-00-05)."""
    original_env = settings.APP_ENV
    original_url = settings.DATABASE_URL
    try:
        settings.APP_ENV = "production"
        settings.DATABASE_URL = "postgresql+psycopg2://user:pass@localhost:5432/db"
        engine = db_module.get_engine()
        assert isinstance(engine.pool, NullPool), f"Expected NullPool, got {type(engine.pool)}"

        settings.APP_ENV = "preview"
        engine_preview = db_module.get_engine()
        assert isinstance(engine_preview.pool, NullPool), f"Expected NullPool, got {type(engine_preview.pool)}"
    finally:
        settings.APP_ENV = original_env
        settings.DATABASE_URL = original_url
