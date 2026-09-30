"""Integration tests for emergency incident creation, idempotency replay, and spatial deduplication (Spec §7.1, CORE-01, CORE-02)."""
from datetime import timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.config import settings
from app.core.security import create_access_token
from app.domain.enums import EmergencyStatus, OfferStatus, Priority, TrackStatus, UserRole
from app.models.emergency import DispatchOffer, Emergency, EmergencyEvent
from app.models.user import User
from app.seed import seed_all


@pytest.fixture
def seeded_env(db_session: Session):
    """Seed Appendix B demo personas and return test citizen."""
    seed_all()

    citizen = (
        db_session.query(User)
        .filter(User.role == UserRole.CITIZEN.value)
        .first()
    )
    if not citizen:
        citizen = User(
            email="priya.test@lifelink.in",
            password_hash="fakehash",
            full_name="Priya Sharma (Test Citizen)",
            role=UserRole.CITIZEN.value,
            phone="+919876543201",
            is_active=True,
        )
        db_session.add(citizen)
        db_session.commit()
        db_session.refresh(citizen)

    token = create_access_token(user_id=citizen.id, role=citizen.role, demo_session_id=citizen.demo_session_id)
    return citizen, token


def test_emergency_creation_successful(client: TestClient, seeded_env, db_session: Session):
    """Verify emergency creation triggers triage, dispatch plan, and initial offers (CORE-01)."""
    citizen, token = seeded_env
    idemp_key = f"create-test-{uuid.uuid4().hex[:8]}"

    payload = {
        "lat": 18.5204,
        "lng": 73.8567,
        "location_accuracy_m": 12.5,
        "location_hint": "Flat 402, Shanti Heights",
        "patient_is_reporter": True,
        "consent_share_medical": False,
        "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
        "triage_input": {
            "quick_type": "BLEEDING",
            "answers": {
                "awake": "yes",
                "breathing": "yes",
                "severe_bleeding": "yes",
            },
            "description": "Deep glass cut on left forearm, bleeding profusely",
        },
        "force_create": False,
    }

    response = client.post(
        "/api/v1/emergencies",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": idemp_key,
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["idempotency_key"] == idemp_key
    assert data["priority"] == Priority.P1_CRITICAL.value
    assert data["emergency_type"] == "BLEEDING"
    assert data["status"] == EmergencyStatus.DISPATCHING.value
    assert data["community_track"] == TrackStatus.OFFERED.value
    assert data["professional_track"] == TrackStatus.OFFERED.value
    assert "community_plan" in data["dispatch_plan"]
    assert "professional_plan" in data["dispatch_plan"]

    # Verify DB records
    emergency_id = uuid.UUID(data["id"])
    emergency = db_session.query(Emergency).filter(Emergency.id == emergency_id).first()
    assert emergency is not None
    assert emergency.reported_by_user_id == citizen.id

    # Verify community offer assigned to candidate #1 (Asha Shinde)
    offers = db_session.query(DispatchOffer).filter(DispatchOffer.emergency_id == emergency_id).all()
    comm_offers = [o for o in offers if o.track == "community"]
    assert len(comm_offers) == 1
    assert comm_offers[0].rank == 1
    assert comm_offers[0].status == OfferStatus.OFFERED.value
    assert comm_offers[0].responder is not None
    assert comm_offers[0].responder.full_name == "Asha Shinde"

    # Verify ambulance offer assigned to ALS unit (Ambulance-1)
    amb_offers = [o for o in offers if o.track == "professional"]
    assert len(amb_offers) == 1
    assert amb_offers[0].rank == 1
    assert amb_offers[0].status == OfferStatus.OFFERED.value
    assert amb_offers[0].ambulance is not None
    assert amb_offers[0].ambulance.callsign == "AMB-01"

    # Verify append-only timeline events
    events = (
        db_session.query(EmergencyEvent)
        .filter(EmergencyEvent.emergency_id == emergency_id)
        .order_by(EmergencyEvent.seq.asc())
        .all()
    )
    event_types = [e.type for e in events]
    assert "EMERGENCY_CREATED" in event_types
    assert "TRIAGE_COMPLETED" in event_types
    assert "OFFER_CREATED" in event_types
    # Monotonic sequence check
    seqs = [e.seq for e in events]
    assert seqs == list(range(1, len(events) + 1))


def test_emergency_creation_idempotent_replay(client: TestClient, seeded_env, db_session: Session):
    """Verify submitting the exact same Idempotency-Key returns existing record (CORE-01, D-01)."""
    citizen, token = seeded_env
    idemp_key = f"replay-key-{uuid.uuid4().hex[:8]}"

    payload = {
        "lat": 18.5204,
        "lng": 73.8567,
        "triage_input": {
            "quick_type": "BLEEDING",
            "answers": {"severe_bleeding": "yes"},
        },
    }

    # First request
    res1 = client.post(
        "/api/v1/emergencies",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idemp_key},
    )
    assert res1.status_code == 201
    em_id_1 = res1.json()["id"]

    # Replay request
    res2 = client.post(
        "/api/v1/emergencies",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idemp_key},
    )
    assert res2.status_code in (200, 201)
    em_id_2 = res2.json()["id"]

    assert em_id_1 == em_id_2

    # Assert DB count for this user and idempotency key is exactly 1
    total = (
        db_session.query(Emergency)
        .filter(Emergency.reported_by_user_id == citizen.id, Emergency.idempotency_key == idemp_key)
        .count()
    )
    assert total == 1


def test_emergency_creation_deduplication_409(client: TestClient, seeded_env):
    """Verify report within 150m and 10min returns HTTP 409 POSSIBLE_DUPLICATE (CORE-02, D-02)."""
    citizen, token = seeded_env

    # First emergency at (18.5204, 73.8567)
    res1 = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": f"dup-1-{uuid.uuid4().hex[:6]}"},
    )
    assert res1.status_code == 201
    existing_id = res1.json()["id"]

    # Second emergency ~44m away at (18.5208, 73.8567) without force_create
    res2 = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5208,
            "lng": 73.8567,
            "triage_input": {"quick_type": "BLEEDING"},
            "force_create": False,
        },
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": f"dup-2-{uuid.uuid4().hex[:6]}"},
    )
    assert res2.status_code == 409
    err = res2.json()
    assert err["error"] == "POSSIBLE_DUPLICATE"
    assert err["existing_emergency_id"] == existing_id
    assert err["can_force_create"] is True
    assert err["distance_m"] < 150.0


def test_emergency_creation_deduplication_force_create_override(client: TestClient, seeded_env, db_session: Session):
    """Verify force_create=true overrides duplicate 409 rejection and creates incident (CORE-02)."""
    citizen, token = seeded_env

    # First emergency by citizen 1
    res1 = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": f"ovr-1-{uuid.uuid4().hex[:6]}"},
    )
    assert res1.status_code == 201
    id1 = res1.json()["id"]

    # Second emergency ~44m away reported by citizen 2 (bystander reporting distinct incident)
    citizen_2 = User(
        email=f"bystander.{uuid.uuid4().hex[:6]}@lifelink.in",
        password_hash="fakehash",
        full_name="Bystander Citizen",
        role=UserRole.CITIZEN.value,
        phone="+919876543209",
        is_active=True,
    )
    db_session.add(citizen_2)
    db_session.commit()
    db_session.refresh(citizen_2)
    token_2 = create_access_token(user_id=citizen_2.id, role=citizen_2.role)

    # Second emergency ~44m away with force_create=True
    res2 = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5208,
            "lng": 73.8567,
            "triage_input": {"quick_type": "BLEEDING"},
            "force_create": True,
        },
        headers={"Authorization": f"Bearer {token_2}", "Idempotency-Key": f"ovr-2-{uuid.uuid4().hex[:6]}"},
    )
    assert res2.status_code == 201
    id2 = res2.json()["id"]

    assert id1 != id2


def test_emergency_creation_coordinate_validation(client: TestClient, seeded_env):
    """Verify coordinate bounds [-90..90] lat and [-180..180] lng are strictly enforced (T-05-06)."""
    citizen, token = seeded_env

    # Out-of-bounds latitude
    res_lat = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 95.0,
            "lng": 73.8567,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_lat.status_code == 422

    # Out-of-bounds longitude
    res_lng = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": -190.0,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_lng.status_code == 422
