"""Integration tests for deterministic lazy advance, row locking, and cascading dispatch (Spec §7.2, CORE-03, CORE-05)."""
from datetime import timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.config import settings
from app.core.security import create_access_token
from app.domain.enums import EmergencyStatus, OfferStatus, TrackStatus, UserRole
from app.models.emergency import DispatchOffer, Emergency, EmergencyEvent
from app.models.user import User
from app.seed import seed_all
from app.services.advance import advance_emergency


@pytest.fixture
def seeded_env(db_session: Session):
    """Seed Appendix B demo personas and return test citizen and token."""
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


def test_advance_before_timeout_is_noop(client: TestClient, seeded_env, db_session: Session):
    """Verify calling advance before 30s timeout leaves candidate #1 offer untouched (CORE-03)."""
    citizen, token = seeded_env
    idemp_key = f"adv-noop-{uuid.uuid4().hex[:8]}"

    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idemp_key},
    )
    assert res.status_code == 201
    em_id = res.json()["id"]

    # Verify initial candidate #1 offer is Asha Shinde
    initial_offer = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .first()
    )
    assert initial_offer is not None
    assert initial_offer.status == OfferStatus.OFFERED.value
    assert initial_offer.responder.full_name == "Asha Shinde"
    initial_offer_id = initial_offer.id

    initial_events_count = (
        db_session.query(EmergencyEvent)
        .filter(EmergencyEvent.emergency_id == em_id)
        .count()
    )

    # Call advance at t=10s (< 30s timeout)
    adv_res = client.post(
        f"/api/v1/emergencies/{em_id}/advance",
        json={"offset_seconds": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert adv_res.status_code == 200

    db_session.expire_all()
    cur_offer = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .first()
    )
    assert cur_offer.id == initial_offer_id
    assert cur_offer.status == OfferStatus.OFFERED.value

    # Verify no new events were appended
    current_events_count = (
        db_session.query(EmergencyEvent)
        .filter(EmergencyEvent.emergency_id == em_id)
        .count()
    )
    assert current_events_count == initial_events_count


def test_advance_past_timeout_expires_and_cascades_to_candidate_2(
    client: TestClient, seeded_env, db_session: Session
):
    """Verify calling advance past 30s expires Asha Shinde and cascades to Ravi Gaikwad (CORE-03, CORE-05)."""
    citizen, token = seeded_env
    idemp_key = f"adv-casc-{uuid.uuid4().hex[:8]}"

    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idemp_key},
    )
    assert res.status_code == 201
    em_id = res.json()["id"]

    # Call advance at t=35s (> 30s timeout)
    adv_res = client.post(
        f"/api/v1/emergencies/{em_id}/advance",
        json={"offset_seconds": 35},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert adv_res.status_code == 200

    db_session.expire_all()
    comm_offers = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .order_by(DispatchOffer.rank.asc())
        .all()
    )

    assert len(comm_offers) == 2

    # Offer 1 (Asha Shinde) must be EXPIRED
    offer_1 = comm_offers[0]
    assert offer_1.rank == 1
    assert offer_1.status == OfferStatus.EXPIRED.value
    assert offer_1.responder.full_name == "Asha Shinde"
    assert offer_1.responded_at is not None

    # Offer 2 (Ravi Gaikwad) must be OFFERED
    offer_2 = comm_offers[1]
    assert offer_2.rank == 2
    assert offer_2.status == OfferStatus.OFFERED.value
    assert offer_2.responder.full_name == "Ravi Gaikwad"

    # Verify chronological timeline events
    timeline_res = client.get(
        f"/api/v1/emergencies/{em_id}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert timeline_res.status_code == 200
    events = timeline_res.json()
    event_types = [e["type"] for e in events]
    assert "OFFER_EXPIRED" in event_types
    assert "OFFER_CREATED" in event_types

    # Ensure strictly monotonic sequence numbers
    seqs = [e["seq"] for e in events]
    assert seqs == list(range(1, len(events) + 1))


def test_advance_polling_triggers_cascade_transparently(
    client: TestClient, seeded_env, db_session: Session
):
    """Verify regular GET /emergencies/{id} transparently triggers timeout evaluation (CORE-03)."""
    citizen, token = seeded_env
    idemp_key = f"adv-poll-{uuid.uuid4().hex[:8]}"

    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idemp_key},
    )
    em_id = res.json()["id"]

    # Manually backdate initial offers expires_at in DB to simulate passage of 35 seconds
    offers = db_session.query(DispatchOffer).filter(DispatchOffer.emergency_id == em_id).all()
    for o in offers:
        o.expires_at = o.expires_at - timedelta(seconds=60)
    db_session.commit()

    # Client performs normal status poll via GET /emergencies/{id}
    poll_res = client.get(
        f"/api/v1/emergencies/{em_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert poll_res.status_code == 200

    # Verify that transparent lazy advance expired candidate #1 and cascaded to candidate #2
    db_session.expire_all()
    comm_offers = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .order_by(DispatchOffer.rank.asc())
        .all()
    )
    assert len(comm_offers) >= 2
    assert comm_offers[0].status == OfferStatus.EXPIRED.value
    assert comm_offers[1].status == OfferStatus.OFFERED.value
    assert comm_offers[1].responder.full_name == "Ravi Gaikwad"


def test_advance_exhaustion_marks_track_unavailable(
    client: TestClient, seeded_env, db_session: Session
):
    """Verify that when all candidates expire, track is marked UNAVAILABLE and incident closes (CORE-03)."""
    citizen, token = seeded_env
    idemp_key = f"adv-exh-{uuid.uuid4().hex[:8]}"

    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idemp_key},
    )
    em_id = res.json()["id"]

    # Keep advancing and expiring offers until candidates run out
    for offset in [40, 80, 120, 160, 200, 240]:
        client.post(
            f"/api/v1/emergencies/{em_id}/advance",
            json={"offset_seconds": offset},
            headers={"Authorization": f"Bearer {token}"},
        )

    db_session.expire_all()
    em = db_session.query(Emergency).filter(Emergency.id == em_id).one()
    # At this point, both community and professional candidates should be exhausted
    assert em.community_track == TrackStatus.UNAVAILABLE.value
    assert em.professional_track == TrackStatus.UNAVAILABLE.value
    assert em.status == EmergencyStatus.NO_COVERAGE_CLOSED.value
    assert em.close_reason == "NO_COVERAGE"


def test_row_lock_concurrency_no_duplicate_events(
    client: TestClient, seeded_env, db_session: Session
):
    """Verify that multiple sequential or concurrent advance calls maintain strictly unique seq numbers (T-05-09)."""
    citizen, token = seeded_env
    idemp_key = f"adv-lock-{uuid.uuid4().hex[:8]}"

    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idemp_key},
    )
    em_id = res.json()["id"]

    # Call advance multiple times with varying offsets
    for offset in [10, 20, 35, 45, 75]:
        r = client.post(
            f"/api/v1/emergencies/{em_id}/advance",
            json={"offset_seconds": offset},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    db_session.expire_all()
    events = (
        db_session.query(EmergencyEvent)
        .filter(EmergencyEvent.emergency_id == em_id)
        .order_by(EmergencyEvent.seq.asc())
        .all()
    )
    seqs = [e.seq for e in events]
    # Verify no gaps and no duplicate sequence numbers
    assert len(seqs) == len(set(seqs))
    assert seqs == list(range(1, len(events) + 1))
