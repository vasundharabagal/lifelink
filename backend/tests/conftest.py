import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.core.db import engine


@pytest.fixture(scope="session")
def db_engine():
    return engine


@pytest.fixture(scope="function")
def db_session():
    """Isolated database session using nested transaction savepoints (D-10).
    
    Any commits within the test will only commit the inner savepoint.
    Teardown rolls back the outer transaction, ensuring test isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.db import get_db

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
