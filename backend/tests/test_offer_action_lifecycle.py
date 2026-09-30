"""Integration tests for dispatch offer action lifecycle, single-active-responder constraint, and incident resolution (CORE-04, CORE-05, CORE-06, Spec §7.3)."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.domain.enums import EmergencyStatus, OfferStatus, TrackStatus, UserRole
from app.models.emergency import DispatchOffer, Emergency, EmergencyEvent
from app.models.user import User
from app.seed import seed_all


@pytest.fixture
def seeded_env(db_session: Session):
    """Seed personas and return test users and tokens."""
    seed_all()

    citizen = db_session.query(User).filter(User.role == UserRole.CITIZEN.value).first()
    asha = db_session.query(User).filter(User.full_name == "Asha Shinde").first()
    ravi = db_session.query(User).filter(User.full_name == "Ravi Gaikwad").first()
    authority = db_session.query(User).filter(User.role == UserRole.AUTHORITY.value).first()

    assert citizen and asha and ravi and authority

    citizen_token = create_access_token(user_id=citizen.id, role=citizen.role, demo_session_id=citizen.demo_session_id)
    asha_token = create_access_token(user_id=asha.id, role=asha.role, demo_session_id=asha.demo_session_id)
    ravi_token = create_access_token(user_id=ravi.id, role=ravi.role, demo_session_id=ravi.demo_session_id)
    auth_token = create_access_token(user_id=authority.id, role=authority.role, demo_session_id=authority.demo_session_id)

    return {
        "citizen": (citizen, citizen_token),
        "asha": (asha, asha_token),
        "ravi": (ravi, ravi_token),
        "authority": (authority, auth_token),
    }


def test_offer_accept_lifecycle(client: TestClient, seeded_env, db_session: Session):
    """Verify responder accepts pending offer, setting track ASSIGNED and incident IN_PROGRESS (CORE-04)."""
    citizen, cit_token = seeded_env["citizen"]
    asha, asha_token = seeded_env["asha"]

    # 1. Citizen creates emergency
    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {cit_token}", "Idempotency-Key": f"acc-{uuid.uuid4().hex[:6]}"},
    )
    assert res.status_code == 201
    em_id = res.json()["id"]

    # 2. Asha queries pending offers
    pending_res = client.get(
        "/api/v1/offers/pending",
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert pending_res.status_code == 200
    offers = pending_res.json()["offers"]
    assert len(offers) >= 1
    target_offer = next(o for o in offers if o["emergency_id"] == em_id)
    assert target_offer["status"] == "OFFERED"
    assert target_offer["location_tier"] == "coarse"  # Pre-accept privacy

    # 3. Asha accepts offer
    action_res = client.post(
        f"/api/v1/offers/{target_offer['id']}/action",
        json={"action": "ACCEPT"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert action_res.status_code == 200
    accepted_offer = action_res.json()
    assert accepted_offer["status"] == "ACCEPTED"
    assert accepted_offer["location_tier"] == "exact"  # Post-accept privacy

    # 4. Verify emergency state updated to IN_PROGRESS and track to ASSIGNED
    db_session.expire_all()
    em = db_session.query(Emergency).filter(Emergency.id == em_id).one()
    assert em.status == EmergencyStatus.IN_PROGRESS.value
    assert em.community_track == TrackStatus.ASSIGNED.value


def test_offer_double_accept_conflict_409(client: TestClient, seeded_env, db_session: Session):
    """Verify atomic single-active-responder constraint returns HTTP 409 OFFER_ALREADY_CLAIMED (CORE-04, T-05-02)."""
    citizen, cit_token = seeded_env["citizen"]
    asha, asha_token = seeded_env["asha"]
    ravi, ravi_token = seeded_env["ravi"]

    # 1. Citizen creates emergency
    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {cit_token}", "Idempotency-Key": f"dbl-{uuid.uuid4().hex[:6]}"},
    )
    em_id = res.json()["id"]

    # Asha's offer
    asha_offer = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .one()
    )

    # Asha accepts
    acc_res = client.post(
        f"/api/v1/offers/{asha_offer.id}/action",
        json={"action": "ACCEPT"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert acc_res.status_code == 200

    # Second concurrent / duplicate accept attempt receives 409 OFFER_ALREADY_CLAIMED
    conf_res = client.post(
        f"/api/v1/offers/{asha_offer.id}/action",
        json={"action": "ACCEPT"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert conf_res.status_code == 409
    err = conf_res.json()
    assert err["error"]["code"] == "OFFER_ALREADY_CLAIMED"


def test_offer_decline_cascades_to_candidate_2(client: TestClient, seeded_env, db_session: Session):
    """Verify declining an offer instantly creates candidate #2 offer in same transaction (CORE-05, D-06)."""
    citizen, cit_token = seeded_env["citizen"]
    asha, asha_token = seeded_env["asha"]

    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {cit_token}", "Idempotency-Key": f"dec-{uuid.uuid4().hex[:6]}"},
    )
    em_id = res.json()["id"]

    initial_offer = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .one()
    )
    assert initial_offer.responder_id == asha.id

    # Asha declines offer
    dec_res = client.post(
        f"/api/v1/offers/{initial_offer.id}/action",
        json={"action": "DECLINE", "decline_reason": "IN_SURGERY"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert dec_res.status_code == 200
    assert dec_res.json()["status"] == "DECLINED"
    assert dec_res.json()["location_tier"] == "revoked"

    # Verify candidate #2 (Ravi Gaikwad) offer was created synchronously
    db_session.expire_all()
    offers = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .order_by(DispatchOffer.rank.asc())
        .all()
    )
    assert len(offers) == 2
    assert offers[0].status == OfferStatus.DECLINED.value
    assert offers[1].rank == 2
    assert offers[1].status == OfferStatus.OFFERED.value
    assert offers[1].responder.full_name == "Ravi Gaikwad"


def test_offer_arrive_and_complete(client: TestClient, seeded_env, db_session: Session):
    """Verify ARRIVE and COMPLETE transitions with reported action checklist (CORE-04)."""
    citizen, cit_token = seeded_env["citizen"]
    asha, asha_token = seeded_env["asha"]

    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {cit_token}", "Idempotency-Key": f"arr-{uuid.uuid4().hex[:6]}"},
    )
    em_id = res.json()["id"]

    offer = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .one()
    )

    # 1. Accept
    client.post(
        f"/api/v1/offers/{offer.id}/action",
        json={"action": "ACCEPT"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )

    # 2. Arrive
    arr_res = client.post(
        f"/api/v1/offers/{offer.id}/action",
        json={"action": "ARRIVE"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert arr_res.status_code == 200
    assert arr_res.json()["status"] == "ARRIVED"

    db_session.expire_all()
    em = db_session.query(Emergency).filter(Emergency.id == em_id).one()
    assert em.community_track == TrackStatus.ON_SCENE.value

    # 3. Complete
    comp_res = client.post(
        f"/api/v1/offers/{offer.id}/action",
        json={
            "action": "COMPLETE",
            "actions_reported": ["direct_pressure_applied", "tourniquet_applied"],
            "notes": "Bleeding controlled, handed over to paramedics.",
        },
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "COMPLETED"
    assert "direct_pressure_applied" in comp_data["actions_reported"]
    assert comp_data["location_tier"] == "revoked"

    db_session.expire_all()
    em = db_session.query(Emergency).filter(Emergency.id == em_id).one()
    assert em.community_track == TrackStatus.DONE.value


def test_offer_scene_unsafe_logs_hazard_and_cascades(client: TestClient, seeded_env, db_session: Session):
    """Verify SCENE_UNSAFE tags incident warning and alerts next volunteer (CORE-04, D-07)."""
    citizen, cit_token = seeded_env["citizen"]
    asha, asha_token = seeded_env["asha"]

    res = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {cit_token}", "Idempotency-Key": f"uns-{uuid.uuid4().hex[:6]}"},
    )
    em_id = res.json()["id"]

    offer = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.track == "community")
        .one()
    )

    # Asha accepts
    client.post(
        f"/api/v1/offers/{offer.id}/action",
        json={"action": "ACCEPT"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )

    # Asha encounters safety hazard
    unsafe_res = client.post(
        f"/api/v1/offers/{offer.id}/action",
        json={"action": "SCENE_UNSAFE", "notes": "Exposed high voltage electrical wire near patient pool"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert unsafe_res.status_code == 200

    # Verify incident plan contains warning
    db_session.expire_all()
    em = db_session.query(Emergency).filter(Emergency.id == em_id).one()
    assert "Exposed high voltage" in em.dispatch_plan.get("scene_safety_warning", "")

    # Verify Ravi received cascaded offer with hazard note
    ravi_offer = (
        db_session.query(DispatchOffer)
        .filter(DispatchOffer.emergency_id == em_id, DispatchOffer.rank == 2)
        .first()
    )
    assert ravi_offer is not None
    assert "Exposed high voltage" in ravi_offer.notes


def test_emergency_cancel_and_resolve_endpoints(client: TestClient, seeded_env, db_session: Session):
    """Verify incident cancellation by citizen and resolution by authority (CORE-06)."""
    citizen, cit_token = seeded_env["citizen"]
    authority, auth_token = seeded_env["authority"]
    asha, asha_token = seeded_env["asha"]

    # 1. Incident 1: Citizen cancels
    res1 = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "BLEEDING"},
        },
        headers={"Authorization": f"Bearer {cit_token}", "Idempotency-Key": f"cn1-{uuid.uuid4().hex[:6]}"},
    )
    em_id_1 = res1.json()["id"]

    # Unauthorized user (Asha) tries to cancel incident -> 403
    unauth_can = client.post(
        f"/api/v1/emergencies/{em_id_1}/cancel",
        json={"reason": "FALSE_ALARM"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert unauth_can.status_code == 403

    # Authorized reporter cancels -> 200
    can_res = client.post(
        f"/api/v1/emergencies/{em_id_1}/cancel",
        json={"reason": "PATIENT_REFUSED_CARE"},
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert can_res.status_code == 200
    assert can_res.json()["status"] == "CANCELLED"
    assert can_res.json()["close_reason"] == "PATIENT_REFUSED_CARE"

    # 2. Incident 2: Authority resolves
    # Need new citizen since citizen 1 already cancelled an incident (or bystander)
    citizen_2 = User(
        email=f"citizen2.{uuid.uuid4().hex[:6]}@lifelink.in",
        password_hash="fakehash",
        full_name="Second Citizen",
        role=UserRole.CITIZEN.value,
        phone="+919876543202",
        is_active=True,
    )
    db_session.add(citizen_2)
    db_session.commit()
    cit2_token = create_access_token(user_id=citizen_2.id, role=citizen_2.role)

    res2 = client.post(
        "/api/v1/emergencies",
        json={
            "lat": 18.5204,
            "lng": 73.8567,
            "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
            "triage_input": {"quick_type": "CHOKING"},
        },
        headers={"Authorization": f"Bearer {cit2_token}", "Idempotency-Key": f"cn2-{uuid.uuid4().hex[:6]}"},
    )
    em_id_2 = res2.json()["id"]

    resolve_res = client.post(
        f"/api/v1/emergencies/{em_id_2}/resolve",
        json={"summary": "Foreign body dislodged by volunteer on scene."},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "COMPLETED"
    assert resolve_res.json()["close_reason"] == "RESOLVED"
