"""End-to-End API Walkthrough of Master Spec Appendix B Incident 1 (CORE-01..07, Spec Appendix B).

Simulates the complete 19-step golden walkthrough:
1. Citizen Priya Sharma creates severe bleeding emergency (P1_CRITICAL).
2. Dual-track dispatch triggers initial offers for Asha Shinde (Community #1) and AMB-01 (ALS Unit #1).
3. Asha Shinde inspects pending offer with coarse ~250m privacy coordinates.
4. Asha Shinde declines offer due to prior clinical commitment.
5. Orchestration cascades instantly in-transaction to Ravi Gaikwad (Paramedic, Rank #2).
6. Ravi Gaikwad accepts offer; location unmasks from coarse to exact coordinates.
7. Ravi Gaikwad reports arrival on scene (TrackStatus: ON_SCENE).
8. Ravi Gaikwad reports first-aid care checklist (pressure, tourniquet) and completes response.
9. Incident is verified with strictly monotonic append-only timeline events.
"""
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
def walkthrough_cast(db_session: Session):
    """Seed Appendix B cast and return actors and authentication tokens."""
    seed_all()

    citizen = db_session.query(User).filter(User.role == UserRole.CITIZEN.value).first()
    asha = db_session.query(User).filter(User.full_name == "Asha Shinde").first()
    ravi = db_session.query(User).filter(User.full_name == "Ravi Gaikwad").first()
    authority = db_session.query(User).filter(User.role == UserRole.AUTHORITY.value).first()

    assert citizen and asha and ravi and authority

    return {
        "citizen": (citizen, create_access_token(user_id=citizen.id, role=citizen.role, demo_session_id=citizen.demo_session_id)),
        "asha": (asha, create_access_token(user_id=asha.id, role=asha.role, demo_session_id=asha.demo_session_id)),
        "ravi": (ravi, create_access_token(user_id=ravi.id, role=ravi.role, demo_session_id=ravi.demo_session_id)),
        "authority": (authority, create_access_token(user_id=authority.id, role=authority.role, demo_session_id=authority.demo_session_id)),
    }


def test_appendix_b_incident_1_complete_api_walkthrough(client: TestClient, walkthrough_cast, db_session: Session):
    """Run Appendix B Incident 1 full interactive walkthrough through public REST API."""
    citizen, cit_token = walkthrough_cast["citizen"]
    asha, asha_token = walkthrough_cast["asha"]
    ravi, ravi_token = walkthrough_cast["ravi"]
    authority, auth_token = walkthrough_cast["authority"]

    # -------------------------------------------------------------
    # Step 1: Citizen creates emergency incident (P1 Severe Bleeding)
    # -------------------------------------------------------------
    create_payload = {
        "lat": 18.5204,
        "lng": 73.8567,
        "location_accuracy_m": 12.0,
        "location_hint": "Flat 402, Shanti Heights, FC Road",
        "patient_is_reporter": True,
        "consent_share_medical": False,
        "demo_session_id": settings.DEFAULT_DEMO_SESSION_ID,
        "triage_input": {
            "quick_type": "BLEEDING",
            "answers": {
                "severe_bleeding": "yes",
                "awake": "yes",
                "breathing": "yes",
            },
        },
    }
    idemp_key = f"app-b-{uuid.uuid4().hex[:8]}"

    res_create = client.post(
        "/api/v1/emergencies",
        json=create_payload,
        headers={"Authorization": f"Bearer {cit_token}", "Idempotency-Key": idemp_key},
    )
    assert res_create.status_code == 201
    emergency = res_create.json()
    em_id = emergency["id"]
    assert emergency["priority"] == "P1_CRITICAL"
    assert emergency["community_track"] == "OFFERED"
    assert emergency["professional_track"] == "OFFERED"

    # -------------------------------------------------------------
    # Step 2: Asha Shinde receives pending offer (coarse privacy tier)
    # -------------------------------------------------------------
    res_asha_pending = client.get(
        "/api/v1/offers/pending",
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert res_asha_pending.status_code == 200
    asha_offers = res_asha_pending.json()["offers"]
    assert len(asha_offers) >= 1
    asha_offer = next(o for o in asha_offers if o["emergency_id"] == em_id)
    assert asha_offer["rank"] == 1
    assert asha_offer["status"] == "OFFERED"
    assert asha_offer["location_tier"] == "coarse"
    assert asha_offer["location_revoked"] is False
    assert (asha_offer["lat"], asha_offer["lng"]) != (18.5204, 73.8567)  # Masked offset

    # -------------------------------------------------------------
    # Step 3: Asha Shinde declines offer due to existing surgery
    # -------------------------------------------------------------
    res_asha_decline = client.post(
        f"/api/v1/offers/{asha_offer['id']}/action",
        json={"action": "DECLINE", "decline_reason": "IN_SURGERY"},
        headers={"Authorization": f"Bearer {asha_token}"},
    )
    assert res_asha_decline.status_code == 200
    declined_data = res_asha_decline.json()
    assert declined_data["status"] == "DECLINED"
    assert declined_data["location_tier"] == "revoked"
    assert declined_data["location_revoked"] is True
    assert declined_data["lat"] is None and declined_data["lng"] is None

    # -------------------------------------------------------------
    # Step 4: System cascaded to Ravi Gaikwad (Candidate #2)
    # -------------------------------------------------------------
    res_ravi_pending = client.get(
        "/api/v1/offers/pending",
        headers={"Authorization": f"Bearer {ravi_token}"},
    )
    assert res_ravi_pending.status_code == 200
    ravi_offers = res_ravi_pending.json()["offers"]
    ravi_offer = next(o for o in ravi_offers if o["emergency_id"] == em_id)
    assert ravi_offer["rank"] == 2
    assert ravi_offer["status"] == "OFFERED"
    assert ravi_offer["location_tier"] == "coarse"

    # -------------------------------------------------------------
    # Step 5: Ravi Gaikwad accepts offer -> exact coordinates unmask
    # -------------------------------------------------------------
    res_ravi_accept = client.post(
        f"/api/v1/offers/{ravi_offer['id']}/action",
        json={"action": "ACCEPT"},
        headers={"Authorization": f"Bearer {ravi_token}"},
    )
    assert res_ravi_accept.status_code == 200
    accepted_data = res_ravi_accept.json()
    assert accepted_data["status"] == "ACCEPTED"
    assert accepted_data["location_tier"] == "exact"
    assert accepted_data["location_revoked"] is False
    assert accepted_data["lat"] == 18.5204
    assert accepted_data["lng"] == 73.8567

    # -------------------------------------------------------------
    # Step 6: Citizen polls and sees Ravi Gaikwad is ASSIGNED
    # -------------------------------------------------------------
    res_cit_poll = client.get(
        f"/api/v1/emergencies/{em_id}",
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert res_cit_poll.status_code == 200
    assert res_cit_poll.json()["community_track"] == "ASSIGNED"
    assert res_cit_poll.json()["status"] == "IN_PROGRESS"

    # -------------------------------------------------------------
    # Step 7: Ravi Gaikwad reports arrival on scene
    # -------------------------------------------------------------
    res_arrive = client.post(
        f"/api/v1/offers/{ravi_offer['id']}/action",
        json={"action": "ARRIVE"},
        headers={"Authorization": f"Bearer {ravi_token}"},
    )
    assert res_arrive.status_code == 200
    assert res_arrive.json()["status"] == "ARRIVED"

    # -------------------------------------------------------------
    # Step 8: Ravi Gaikwad completes first aid care & reports actions
    # -------------------------------------------------------------
    res_complete = client.post(
        f"/api/v1/offers/{ravi_offer['id']}/action",
        json={
            "action": "COMPLETE",
            "actions_reported": ["direct_pressure_applied", "hemostatic_dressing_applied"],
            "notes": "Patient bleeding successfully controlled. Stable vitals.",
        },
        headers={"Authorization": f"Bearer {ravi_token}"},
    )
    assert res_complete.status_code == 200
    comp_data = res_complete.json()
    assert comp_data["status"] == "COMPLETED"
    assert comp_data["location_tier"] == "revoked"  # Coordinates revoked upon mission end

    # -------------------------------------------------------------
    # Step 9: Authority completes formal incident resolution
    # -------------------------------------------------------------
    res_resolve = client.post(
        f"/api/v1/emergencies/{em_id}/resolve",
        json={"summary": "Patient handed over to ALS Ambulance AMB-01; transferred to Sassoon Hospital."},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "COMPLETED"

    # -------------------------------------------------------------
    # Step 10: Verify append-only timeline event audit log
    # -------------------------------------------------------------
    res_timeline = client.get(
        f"/api/v1/emergencies/{em_id}/timeline",
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert res_timeline.status_code == 200
    events = res_timeline.json()
    event_types = [e["type"] for e in events]

    assert "EMERGENCY_CREATED" in event_types
    assert "TRIAGE_COMPLETED" in event_types
    assert "OFFER_CREATED" in event_types
    assert "OFFER_DECLINED" in event_types
    assert "OFFER_ACCEPTED" in event_types
    assert "RESPONDER_ARRIVED" in event_types
    assert "RESPONDER_COMPLETED" in event_types
    assert "EMERGENCY_COMPLETED" in event_types

    # Ensure monotonic sequence numbering with no gaps
    seqs = [e["seq"] for e in events]
    assert seqs == list(range(1, len(events) + 1))
