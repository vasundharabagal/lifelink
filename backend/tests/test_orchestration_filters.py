"""Unit tests for response orchestration hard eligibility filters (ORCH-01, Spec §6.3)."""
from datetime import datetime, date, timedelta, timezone
import uuid
import pytest
from app.core.clock import Clock
from app.domain.enums import (
    ResponderCategory,
    ResponderReadiness,
    CredentialStatus,
    AmbulanceUnitType,
    AmbulanceUnitStatus,
    Priority,
    EmergencyType,
    SkillCode,
    EligibilityRejectionReason,
)
from app.schemas.triage import RequiredSkill
from app.orchestration.schemas import (
    CandidateProfile,
    CandidateSkill,
    CandidateCredential,
    AmbulanceCandidate,
    EmergencyContext,
)
from app.orchestration.filters import (
    evaluate_responder_eligibility,
    evaluate_ambulance_eligibility,
)


@pytest.fixture
def test_clock():
    """Deterministic clock set to 2026-10-01 12:00:00 UTC."""
    return Clock()


@pytest.fixture
def base_emergency():
    """Base P1 emergency context at DEMO_CENTER."""
    return EmergencyContext(
        emergency_id=uuid.uuid4(),
        lat=18.5204,
        lng=73.8567,
        priority=Priority.P1_CRITICAL,
        emergency_type=EmergencyType.BLEEDING,
        protocol_id="PROT_SEVERE_BLEEDING",
        required_skills=[RequiredSkill(skill=SkillCode.BLEEDING_CONTROL, min_level=2)],
        patient_user_id=uuid.uuid4(),
        reported_by_user_id=uuid.uuid4(),
        demo_session_id=None,
    )


@pytest.fixture
def base_candidate(test_clock):
    """Base fully-eligible responder (similar to Asha: nurse, level 3 bleeding control, 800m away)."""
    now = test_clock.now()
    return CandidateProfile(
        user_id=uuid.uuid4(),
        full_name="Asha Shinde",
        category=ResponderCategory.NURSE,
        is_active=True,
        readiness=ResponderReadiness.AVAILABLE,
        service_radius_m=3000,
        last_lat=18.5255,
        last_lng=73.8620,
        last_location_at=now,
        pinned_location=False,
        acceptance_rate=1.0,
        responses_24h=0,
        demo_session_id=None,
        skills=[
            CandidateSkill(skill_code=SkillCode.BLEEDING_CONTROL, level=3),
            CandidateSkill(skill_code=SkillCode.TRAUMA_RESPONSE, level=3),
        ],
        credentials=[
            CandidateCredential(
                credential_type="Nursing Registration",
                status=CredentialStatus.VERIFIED,
                expires_on=now.date() + timedelta(days=365),
            )
        ],
    )


def test_eligible_responder_passes(base_candidate, base_emergency, test_clock):
    """A verified, available, qualified responder within radius passes eligibility."""
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is None


def test_filter_not_verified_pending(base_candidate, base_emergency, test_clock):
    """Pending credentials must trigger NOT_VERIFIED."""
    base_candidate.credentials[0].status = CredentialStatus.PENDING
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.NOT_VERIFIED in rejection.reason_codes


def test_filter_not_verified_expired(base_candidate, base_emergency, test_clock):
    """Expired credentials must trigger NOT_VERIFIED."""
    base_candidate.credentials[0].expires_on = test_clock.now().date() - timedelta(days=1)
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.NOT_VERIFIED in rejection.reason_codes


def test_filter_not_available_readiness(base_candidate, base_emergency, test_clock):
    """Readiness off_duty or busy triggers NOT_AVAILABLE."""
    base_candidate.readiness = ResponderReadiness.OFF_DUTY
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.NOT_AVAILABLE in rejection.reason_codes


def test_filter_not_available_cooldown(base_candidate, base_emergency, test_clock):
    """Active cooldown in the future triggers NOT_AVAILABLE."""
    base_candidate.cooldown_until = test_clock.now() + timedelta(seconds=60)
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.NOT_AVAILABLE in rejection.reason_codes


def test_filter_active_assignment(base_candidate, base_emergency, test_clock):
    """Responder with active assignment triggers ACTIVE_ASSIGNMENT."""
    base_emergency.active_responder_ids.add(base_candidate.user_id)
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.ACTIVE_ASSIGNMENT in rejection.reason_codes


def test_filter_already_declined_or_expired(base_candidate, base_emergency, test_clock):
    """Responder who already declined triggers ALREADY_DECLINED_OR_EXPIRED."""
    base_emergency.excluded_responder_ids.add(base_candidate.user_id)
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.ALREADY_DECLINED_OR_EXPIRED in rejection.reason_codes


def test_filter_skill_mismatch(base_candidate, base_emergency, test_clock):
    """Responder lacking required bleeding control skill triggers SKILL_MISMATCH."""
    # Karan persona: only holds CPR level 1
    base_candidate.skills = [CandidateSkill(skill_code=SkillCode.CPR_AED, level=1)]
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.SKILL_MISMATCH in rejection.reason_codes


def test_filter_skill_insufficient_level(base_candidate, base_emergency, test_clock):
    """Responder holding bleeding_control level 1 when level 2 is required triggers SKILL_MISMATCH."""
    base_candidate.skills = [CandidateSkill(skill_code=SkillCode.BLEEDING_CONTROL, level=1)]
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.SKILL_MISMATCH in rejection.reason_codes


def test_filter_location_unknown(base_candidate, base_emergency, test_clock):
    """Missing coordinates triggers LOCATION_UNKNOWN."""
    base_candidate.last_lat = None
    base_candidate.last_lng = None
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.LOCATION_UNKNOWN in rejection.reason_codes


def test_filter_location_stale(base_candidate, base_emergency, test_clock):
    """Telemetry older than 300s with pinned_location=False triggers LOCATION_STALE."""
    base_candidate.pinned_location = False
    base_candidate.last_location_at = test_clock.now() - timedelta(seconds=301)
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.LOCATION_STALE in rejection.reason_codes


def test_filter_pinned_location_bypasses_stale(base_candidate, base_emergency, test_clock):
    """Pinned demo personas bypass location freshness check."""
    base_candidate.pinned_location = True
    base_candidate.last_location_at = test_clock.now() - timedelta(hours=24)
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is None


def test_filter_outside_service_radius(base_candidate, base_emergency, test_clock):
    """Distance exceeding service radius triggers OUTSIDE_SERVICE_RADIUS."""
    # Sana persona: 4.5km away with 3km radius
    # 4.5 km offset at ~0.04 degrees
    base_candidate.service_radius_m = 3000
    base_candidate.last_lat = base_emergency.lat + 0.041
    base_candidate.last_lng = base_emergency.lng
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.OUTSIDE_SERVICE_RADIUS in rejection.reason_codes


def test_filter_is_patient_or_reporter(base_candidate, base_emergency, test_clock):
    """Patient cannot be dispatched to their own emergency."""
    base_emergency.patient_user_id = base_candidate.user_id
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.IS_PATIENT in rejection.reason_codes


def test_filter_scope_mismatch(base_candidate, base_emergency, test_clock):
    """Mismatch in demo session triggers SCOPE_MISMATCH."""
    base_emergency.demo_session_id = uuid.uuid4()
    base_candidate.demo_session_id = uuid.uuid4()
    rejection = evaluate_responder_eligibility(base_candidate, base_emergency, test_clock)
    assert rejection is not None
    assert EligibilityRejectionReason.SCOPE_MISMATCH in rejection.reason_codes


def test_ambulance_eligibility_and_filters(base_emergency, test_clock):
    """Verify ambulance unit hard eligibility filters."""
    unit = AmbulanceCandidate(
        id=uuid.uuid4(),
        callsign="Amb-1",
        unit_type=AmbulanceUnitType.ADVANCED,
        status=AmbulanceUnitStatus.AVAILABLE,
        lat=18.5300,
        lng=73.8600,
        demo_session_id=None,
    )

    # 1. Available unit passes
    assert evaluate_ambulance_eligibility(unit, base_emergency, test_clock) is None

    # 2. Busy unit rejected
    unit.status = AmbulanceUnitStatus.BUSY
    rej_busy = evaluate_ambulance_eligibility(unit, base_emergency, test_clock)
    assert rej_busy is not None
    assert EligibilityRejectionReason.UNIT_NOT_AVAILABLE in rej_busy.reason_codes

    # 3. Active assignment rejected
    unit.status = AmbulanceUnitStatus.AVAILABLE
    base_emergency.active_ambulance_ids.add(unit.id)
    rej_active = evaluate_ambulance_eligibility(unit, base_emergency, test_clock)
    assert rej_active is not None
    assert EligibilityRejectionReason.ACTIVE_ASSIGNMENT in rej_active.reason_codes

    # 4. Scope mismatch rejected
    base_emergency.active_ambulance_ids.clear()
    unit.demo_session_id = uuid.uuid4()
    rej_scope = evaluate_ambulance_eligibility(unit, base_emergency, test_clock)
    assert rej_scope is not None
    assert EligibilityRejectionReason.SCOPE_MISMATCH in rej_scope.reason_codes
