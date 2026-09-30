"""Integration tests for response orchestration database loader and Appendix B persona verification (ORCH-01..04)."""
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from sqlalchemy.orm import Session
from app.core.clock import Clock
from app.core.config import settings
from app.domain.enums import (
    Priority,
    EmergencyType,
    SkillCode,
    EligibilityRejectionReason,
    OfferStatus,
)
from app.models import User, Emergency, DispatchOffer, DemoSession
from app.seed import seed_all
from app.orchestration.service import find_and_rank_candidates


@pytest.fixture
def test_clock():
    return Clock()


@pytest.fixture
def seeded_db(db_session: Session, test_clock):
    """Seed test database with default demo session and Appendix B personas."""
    seed_all()
    return db_session


def test_orchestration_appendix_b_seeded_cast(seeded_db: Session, test_clock):
    """Verify response orchestration matching against Appendix B seeded demo cast (Spec Appendix B)."""
    default_session_id = uuid.UUID(settings.DEFAULT_DEMO_SESSION_ID)

    # 1. Fetch citizen demo persona
    citizen = seeded_db.query(User).filter(User.email == "citizen.demo@lifelink.demo").first()
    assert citizen is not None

    # 2. Create emergency at DEMO_CENTER with P1 bleeding triage (requires bleeding_control >= 2)
    emergency = Emergency(
        id=uuid.uuid4(),
        patient_user_id=citizen.id,
        reported_by_user_id=citizen.id,
        idempotency_key=f"test-orch-demo-{uuid.uuid4()}",
        status="TRIAGED",
        community_track="NOT_STARTED",
        professional_track="NOT_STARTED",
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.BLEEDING.value,
        lat=settings.DEMO_CENTER_LAT,
        lng=settings.DEMO_CENTER_LNG,
        demo_session_id=default_session_id,
        triage={
            "priority": Priority.P1_CRITICAL.value,
            "emergency_type": EmergencyType.BLEEDING.value,
            "protocol_id": "PROT_SEVERE_BLEEDING",
            "ambulance_required": True,
            "required_skills": [
                {"skill": "bleeding_control", "min_level": 2}
            ],
        },
    )
    seeded_db.add(emergency)
    seeded_db.commit()

    # 3. Execute orchestration
    result = find_and_rank_candidates(seeded_db, emergency.id, test_clock)

    # 4. Verify Community Track Rankings
    # Asha (#1), Ravi (#2), Dr. Devendra More (#3), Meera (#4)
    assert len(result.community_plan) == 4
    assert result.community_plan[0].full_name == "Asha Shinde"
    assert result.community_plan[0].rank == 1

    assert result.community_plan[1].full_name == "Ravi Gaikwad"
    assert result.community_plan[1].rank == 2

    assert result.community_plan[2].full_name == "Dr. Devendra More"
    assert result.community_plan[2].rank == 3

    assert result.community_plan[3].full_name == "Meera Kulkarni"
    assert result.community_plan[3].rank == 4

    # 5. Verify Community Track Rejection Reason Codes
    rejection_map = {
        r.name_or_callsign: r.reason_codes
        for r in result.community_explanation.rejected
    }

    # Karan: closest (0.3 km) but CPR-1 only -> rejected SKILL_MISMATCH
    assert "Karan Joshi" in rejection_map
    assert EligibilityRejectionReason.SKILL_MISMATCH in rejection_map["Karan Joshi"]

    # Dr. Iyer: busy on assignment -> rejected NOT_AVAILABLE
    assert "Dr. Subhash Iyer" in rejection_map
    assert EligibilityRejectionReason.NOT_AVAILABLE in rejection_map["Dr. Subhash Iyer"]

    # Sana: 4.5 km away with 3.0 km radius -> rejected OUTSIDE_SERVICE_RADIUS
    assert "Sana Khan" in rejection_map
    assert EligibilityRejectionReason.OUTSIDE_SERVICE_RADIUS in rejection_map["Sana Khan"]

    # Vik: off duty -> rejected NOT_AVAILABLE
    assert "Vikram Jadhav" in rejection_map
    assert EligibilityRejectionReason.NOT_AVAILABLE in rejection_map["Vikram Jadhav"]

    # Nita: credential expired -> rejected NOT_VERIFIED
    assert "Nita Deshmukh" in rejection_map
    assert EligibilityRejectionReason.NOT_VERIFIED in rejection_map["Nita Deshmukh"]

    # Omar: credential pending -> rejected NOT_VERIFIED
    assert "Omar Shaikh" in rejection_map
    assert EligibilityRejectionReason.NOT_VERIFIED in rejection_map["Omar Shaikh"]

    # 6. Verify Professional Track Rankings
    # Amb-1 (Advanced ALS) ranks #1, Amb-2 (Basic BLS) ranks #2
    assert len(result.professional_plan) == 2
    assert result.professional_plan[0].callsign == "AMB-01"
    assert result.professional_plan[0].rank == 1

    assert result.professional_plan[1].callsign == "AMB-02"
    assert result.professional_plan[1].rank == 2

    # Amb-3: busy status -> rejected UNIT_NOT_AVAILABLE
    amb_rejection_map = {
        r.name_or_callsign: r.reason_codes
        for r in result.professional_explanation.rejected
    }
    assert "AMB-03" in amb_rejection_map
    assert EligibilityRejectionReason.UNIT_NOT_AVAILABLE in amb_rejection_map["AMB-03"]

    # 7. Verify Citizen Summaries
    assert "nurse" in result.community_explanation.citizen_summary.lower()
    assert "ambulance" in result.professional_explanation.citizen_summary.lower()


def test_orchestration_cascading_dispatch_offer_decline(seeded_db: Session, test_clock):
    """Verify that declining an offer moves the responder to rejected and cascades Ravi to #1."""
    default_session_id = uuid.UUID(settings.DEFAULT_DEMO_SESSION_ID)
    citizen = seeded_db.query(User).filter(User.email == "citizen.demo@lifelink.demo").first()
    asha = seeded_db.query(User).filter(User.email == "asha.nurse@lifelink.demo").first()

    emergency = Emergency(
        id=uuid.uuid4(),
        patient_user_id=citizen.id,
        reported_by_user_id=citizen.id,
        idempotency_key=f"test-orch-decline-{uuid.uuid4()}",
        status="DISPATCHING",
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.BLEEDING.value,
        lat=settings.DEMO_CENTER_LAT,
        lng=settings.DEMO_CENTER_LNG,
        demo_session_id=default_session_id,
        triage={
            "priority": Priority.P1_CRITICAL.value,
            "emergency_type": EmergencyType.BLEEDING.value,
            "protocol_id": "PROT_SEVERE_BLEEDING",
            "ambulance_required": True,
            "required_skills": [{"skill": "bleeding_control", "min_level": 2}],
        },
    )
    seeded_db.add(emergency)
    seeded_db.flush()

    # Simulate Asha previously declining the offer
    decline_offer = DispatchOffer(
        id=uuid.uuid4(),
        emergency_id=emergency.id,
        track="community",
        target_kind="responder",
        responder_id=asha.id,
        rank=1,
        status=OfferStatus.DECLINED.value,
        expires_at=test_clock.now() + timedelta(seconds=30),
        responded_at=test_clock.now(),
        decline_reason="unavailable",
    )
    seeded_db.add(decline_offer)
    seeded_db.commit()

    # Re-run orchestration
    result = find_and_rank_candidates(seeded_db, emergency.id, test_clock)

    # Asha is now rejected with ALREADY_DECLINED_OR_EXPIRED
    rejection_map = {
        r.name_or_callsign: r.reason_codes
        for r in result.community_explanation.rejected
    }
    assert "Asha Shinde" in rejection_map
    assert EligibilityRejectionReason.ALREADY_DECLINED_OR_EXPIRED in rejection_map["Asha Shinde"]

    # Ravi Gaikwad cascades to #1!
    assert len(result.community_plan) == 3
    assert result.community_plan[0].full_name == "Ravi Gaikwad"
    assert result.community_plan[0].rank == 1

    # Dr. Devendra More cascades to #2!
    assert result.community_plan[1].full_name == "Dr. Devendra More"
    assert result.community_plan[1].rank == 2

    # Meera Kulkarni cascades to #3!
    assert result.community_plan[2].full_name == "Meera Kulkarni"
    assert result.community_plan[2].rank == 3


def test_orchestration_bounding_box_prefilter_excludes_distant_responders(seeded_db: Session, test_clock):
    """Verify that responders far outside the bounding box (50 km) are excluded by SQL prefilter."""
    default_session_id = uuid.UUID(settings.DEFAULT_DEMO_SESSION_ID)
    citizen = seeded_db.query(User).filter(User.email == "citizen.demo@lifelink.demo").first()

    # Create distant responder 50 km away (0.45 deg latitude offset)
    from app.models.responder import ResponderProfile, ResponderSkill, ResponderCredential
    from app.domain.enums import UserRole, ResponderReadiness, ResponderCategory, CredentialStatus

    distant_user = User(
        id=uuid.uuid4(),
        role=UserRole.RESPONDER.value,
        email="distant.nurse@lifelink.demo",
        password_hash="dummy_hash",
        full_name="Distant Responder",
        is_active=True,
        demo_session_id=default_session_id,
    )
    distant_profile = ResponderProfile(
        user_id=distant_user.id,
        category=ResponderCategory.NURSE.value,
        readiness=ResponderReadiness.AVAILABLE.value,
        service_radius_m=3000,
        last_lat=settings.DEMO_CENTER_LAT + 0.45,  # ~50 km away
        last_lng=settings.DEMO_CENTER_LNG,
        last_location_at=test_clock.now(),
        pinned_location=True,
    )
    distant_skill = ResponderSkill(
        responder_id=distant_user.id,
        skill_code="bleeding_control",
        level=3,
    )
    distant_cred = ResponderCredential(
        id=uuid.uuid4(),
        responder_id=distant_user.id,
        credential_type="Nursing",
        issuer="MNC",
        reference_no="DISTANT-01",
        expires_on=test_clock.now().date() + timedelta(days=365),
        status=CredentialStatus.VERIFIED.value,
    )
    seeded_db.add_all([distant_user, distant_profile, distant_skill, distant_cred])

    emergency = Emergency(
        id=uuid.uuid4(),
        patient_user_id=citizen.id,
        reported_by_user_id=citizen.id,
        idempotency_key=f"test-orch-bbox-{uuid.uuid4()}",
        status="TRIAGED",
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.BLEEDING.value,
        lat=settings.DEMO_CENTER_LAT,
        lng=settings.DEMO_CENTER_LNG,
        demo_session_id=default_session_id,
        triage={
            "priority": Priority.P1_CRITICAL.value,
            "emergency_type": EmergencyType.BLEEDING.value,
            "protocol_id": "PROT_SEVERE_BLEEDING",
            "ambulance_required": True,
            "required_skills": [{"skill": "bleeding_control", "min_level": 2}],
        },
    )
    seeded_db.add(emergency)
    seeded_db.commit()

    # Search with default 5000m (5 km) bounding box
    result = find_and_rank_candidates(seeded_db, emergency.id, test_clock, max_search_radius_m=5000)

    # Distant responder must NOT be in ranked community plan
    ranked_names = [c.full_name for c in result.community_plan]
    assert "Distant Responder" not in ranked_names

    # Distant responder must NOT even be in rejected list because they were excluded at the SQL level
    rejected_names = [r.name_or_callsign for r in result.community_explanation.rejected]
    assert "Distant Responder" not in rejected_names
