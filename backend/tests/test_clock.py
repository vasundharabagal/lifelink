import ast
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from app.core.clock import Clock, get_clock
from app.models.demo import DemoSession


def test_clock_real_time():
    """Verify Clock returns timezone-aware UTC datetime matching system time."""
    clock = Clock()
    sys_now = datetime.now(timezone.utc)
    clock_now = clock.now()

    assert clock_now.tzinfo is not None
    assert abs((clock_now - sys_now).total_seconds()) < 1.0


def test_clock_demo_session_offset(db_session):
    """Verify Clock adds session-specific virtual offset."""
    clock = Clock()
    session = DemoSession(
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        clock_offset_s=120,
    )
    db_session.add(session)
    db_session.flush()

    sys_now = datetime.now(timezone.utc)
    virtual_now = clock.now(demo_session_id=session.id, db=db_session)

    expected_diff = (virtual_now - sys_now).total_seconds()
    assert 118.0 <= expected_diff <= 122.0


def test_clock_advance_and_reset(db_session):
    """Verify advancing and resetting the virtual clock offset."""
    clock = Clock()
    session = DemoSession(
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        clock_offset_s=0,
    )
    db_session.add(session)
    db_session.commit()

    # Advance by 45 seconds
    new_virtual = clock.advance(demo_session_id=session.id, seconds=45, db=db_session)
    assert session.clock_offset_s == 45
    diff = (new_virtual - datetime.now(timezone.utc)).total_seconds()
    assert 43.0 <= diff <= 47.0

    # Reset
    reset_virtual = clock.reset(demo_session_id=session.id, db=db_session)
    assert session.clock_offset_s == 0
    diff_reset = abs((reset_virtual - datetime.now(timezone.utc)).total_seconds())
    assert diff_reset < 1.0


def test_get_clock_dependency():
    """Verify get_clock returns the Clock singleton."""
    c1 = get_clock()
    c2 = get_clock()
    assert isinstance(c1, Clock)
    assert c1 is c2


def test_no_direct_datetime_now():
    """AST scanner: Ban direct datetime.now() and datetime.utcnow() in domain/services/api (DATA-04, D-15).
    
    All application time reads must go through Clock.now(demo_session_id, db).
    Core clock abstraction (backend/app/core/clock.py) is the sole permitted caller.
    """
    backend_app_dir = Path(__file__).resolve().parent.parent / "app"
    prohibited_dirs = ["domain", "services", "api"]
    violations = []

    for subdir_name in prohibited_dirs:
        target_dir = backend_app_dir / subdir_name
        if not target_dir.exists():
            continue

        for py_file in target_dir.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check func: e.g. datetime.now(...) or datetime.utcnow(...)
                    func = node.func
                    if isinstance(func, ast.Attribute) and func.attr in ("now", "utcnow"):
                        if isinstance(func.value, ast.Name) and func.value.id == "datetime":
                            violations.append(f"{py_file.name}:{node.lineno} calls datetime.{func.attr}()")
                    elif isinstance(func, ast.Name) and func.id in ("now", "utcnow"):
                        violations.append(f"{py_file.name}:{node.lineno} calls {func.id}()")

    assert not violations, f"Direct datetime calls forbidden outside core/clock.py: {violations}"
