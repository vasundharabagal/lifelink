from pathlib import Path
from alembic.config import Config
from alembic import command
from sqlalchemy import inspect
from app.core.db import engine


def test_alembic_roundtrip_migrations():
    """Verify clean downgrade to base and upgrade back to head."""
    ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    
    # Downgrade to base
    command.downgrade(cfg, "base")
    
    inspector = inspect(engine)
    tables_after_downgrade = inspector.get_table_names()
    assert "emergencies" not in tables_after_downgrade
    assert "dispatch_offers" not in tables_after_downgrade
    
    # Upgrade back to head
    command.upgrade(cfg, "head")
    
    inspector = inspect(engine)
    tables_after_upgrade = set(inspector.get_table_names())
    expected_tables = {
        "users",
        "medical_profiles",
        "responder_profiles",
        "responder_skills",
        "responder_credentials",
        "ambulance_units",
        "emergencies",
        "dispatch_offers",
        "emergency_events",
        "audit_logs",
        "demo_sessions",
    }
    assert expected_tables.issubset(tables_after_upgrade)
