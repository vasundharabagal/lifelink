"""Unit tests for multi-factor candidate scoring and deterministic tie-breaking (ORCH-02, ORCH-04)."""
import uuid
import pytest
from app.core.clock import Clock
from app.core.config import Settings
from app.domain.enums import (
    ResponderCategory,
    ResponderReadiness,
    CredentialStatus,
    AmbulanceUnitType,
    AmbulanceUnitStatus,
    Priority,
    EmergencyType,
    SkillCode,
)
from app.schemas.triage import RequiredSkill
from app.orchestration.schemas import (
    CandidateProfile,
    CandidateSkill,
    CandidateCredential,
    AmbulanceCandidate,
    EmergencyContext,
    ScoreBreakdown,
    ScoredCandidate,
    AmbulanceScoreBreakdown,
    ScoredAmbulance,
)
from app.orchestration.scoring import (
    calculate_skill_score,
    calculate_eta_score,
    calculate_fairness_score,
    calculate_reliability_score,
    calculate_credential_tier_score,
    calculate_radius_headroom_score,
    calculate_ambulance_suitability_score,
    calculate_ambulance_eta_score,
    calculate_ambulance_fairness_score,
    score_responder,
    score_ambulance,
    rank_scored_responders,
    rank_scored_ambulances,
)


@pytest.fixture
def config():
    return Settings()


@pytest.fixture
def test_clock():
    return Clock()


@pytest.fixture
def emergency():
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
    )


# ---------------------------------------------------------------------------
# Community Scoring Component Tests
# ---------------------------------------------------------------------------

def test_calculate_skill_score_curves():
    """Verify skill scoring base 22, surplus 4, secondary 2, and 30 cap."""
    reqs = [RequiredSkill(skill=SkillCode.BLEEDING_CONTROL, min_level=2)]

    # 1. Exact match (level 2) = 22.0
    skills_exact = [CandidateSkill(skill_code=SkillCode.BLEEDING_CONTROL, level=2)]
    assert calculate_skill_score(skills_exact, reqs, EmergencyType.BLEEDING) == 22.0

    # 2. Surplus match (level 3) = 22 + 4 = 26.0
    skills_surplus = [CandidateSkill(skill_code=SkillCode.BLEEDING_CONTROL, level=3)]
    assert calculate_skill_score(skills_surplus, reqs, EmergencyType.BLEEDING) == 26.0

    # 3. Surplus + 1 secondary skill = 26 + 2 = 28.0
    skills_with_sec = [
        CandidateSkill(skill_code=SkillCode.BLEEDING_CONTROL, level=3),
        CandidateSkill(skill_code=SkillCode.CPR_AED, level=2),
    ]
    assert calculate_skill_score(skills_with_sec, reqs, EmergencyType.BLEEDING) == 28.0

    # 4. Surplus + 3 secondary skills = 26 + 6 = 32 -> capped at 30.0
    skills_capped = [
        CandidateSkill(skill_code=SkillCode.BLEEDING_CONTROL, level=3),
        CandidateSkill(skill_code=SkillCode.CPR_AED, level=2),
        CandidateSkill(skill_code=SkillCode.TRAUMA_RESPONSE, level=2),
        CandidateSkill(skill_code=SkillCode.BASIC_FIRST_AID, level=2),
    ]
    assert calculate_skill_score(skills_capped, reqs, EmergencyType.BLEEDING) == 30.0


def test_calculate_eta_score_curve():
    """Verify 30 pt linear ETA curve."""
    assert calculate_eta_score(0, 900) == 30.0
    assert calculate_eta_score(450, 900) == 15.0
    assert calculate_eta_score(900, 900) == 0.0
    assert calculate_eta_score(1200, 900) == 0.0  # clamped to 0


def test_calculate_fairness_score_curve():
    """Verify 15 pt linear fairness curve."""
    assert calculate_fairness_score(0) == 15.0
    assert calculate_fairness_score(2) == 9.0  # 15 * (1 - 0.4) = 9.0
    assert calculate_fairness_score(5) == 0.0
    assert calculate_fairness_score(10) == 0.0  # clamped to 0


def test_calculate_reliability_score_curve():
    """Verify 10 pt reliability curve."""
    assert calculate_reliability_score(1.0) == 10.0
    assert calculate_reliability_score(0.75) == 7.5
    assert calculate_reliability_score(0.0) == 0.0


def test_calculate_credential_tier_score():
    """Verify 10 pt credential tier categories."""
    assert calculate_credential_tier_score(ResponderCategory.DOCTOR) == 10.0
    assert calculate_credential_tier_score(ResponderCategory.NURSE) == 10.0
    assert calculate_credential_tier_score(ResponderCategory.PARAMEDIC) == 10.0
    assert calculate_credential_tier_score(ResponderCategory.EMT) == 7.0
    assert calculate_credential_tier_score(ResponderCategory.CERTIFIED_FIRST_AIDER) == 7.0
    assert calculate_credential_tier_score(ResponderCategory.MEDICAL_VOLUNTEER) == 4.0
    assert calculate_credential_tier_score(ResponderCategory.STUDENT_RESPONDER) == 4.0
    assert calculate_credential_tier_score(ResponderCategory.OTHER) == 2.0


def test_calculate_radius_headroom_score():
    """Verify 5 pt radius headroom curve (D-07)."""
    # 5.0 pts when distance <= 50% radius
    assert calculate_radius_headroom_score(500, 3000) == 5.0
    assert calculate_radius_headroom_score(1500, 3000) == 5.0

    # Linearly scales down from 5.0 to 0.0 between 50% and 100%
    # At 75% (2250m / 3000m): 10 * (1 - 0.75) = 2.5 pts
    assert calculate_radius_headroom_score(2250, 3000) == 2.5

    # At 100% (3000m / 3000m): 0.0 pts
    assert calculate_radius_headroom_score(3000, 3000) == 0.0
    # Over 100%: 0.0 pts
    assert calculate_radius_headroom_score(3500, 3000) == 0.0


# ---------------------------------------------------------------------------
# Ambulance Unit Scoring Tests
# ---------------------------------------------------------------------------

def test_calculate_ambulance_suitability_p1_vs_p2():
    """Verify ALS vs BLS preference curve based on emergency priority (D-02)."""
    # For P1: ALS gets 20, BLS gets 10
    assert calculate_ambulance_suitability_score(AmbulanceUnitType.ADVANCED, Priority.P1_CRITICAL) == 20.0
    assert calculate_ambulance_suitability_score(AmbulanceUnitType.BASIC, Priority.P1_CRITICAL) == 10.0

    # For P2 / P3: BLS gets 20, ALS gets 15 (preserving critical ALS)
    assert calculate_ambulance_suitability_score(AmbulanceUnitType.BASIC, Priority.P2_SERIOUS) == 20.0
    assert calculate_ambulance_suitability_score(AmbulanceUnitType.ADVANCED, Priority.P2_SERIOUS) == 15.0
    assert calculate_ambulance_suitability_score(AmbulanceUnitType.BASIC, Priority.P3_STABLE) == 20.0
    assert calculate_ambulance_suitability_score(AmbulanceUnitType.ADVANCED, Priority.P3_STABLE) == 15.0


def test_calculate_ambulance_eta_and_fairness():
    """Verify ambulance 70pt ETA and 10pt fairness curves."""
    assert calculate_ambulance_eta_score(0, 900) == 70.0
    assert calculate_ambulance_eta_score(450, 900) == 35.0
    assert calculate_ambulance_eta_score(900, 900) == 0.0

    assert calculate_ambulance_fairness_score(0) == 10.0
    assert calculate_ambulance_fairness_score(2) == 6.0
    assert calculate_ambulance_fairness_score(5) == 0.0


# ---------------------------------------------------------------------------
# Deterministic Tie-Breaking Tests
# ---------------------------------------------------------------------------

def test_rank_scored_responders_tie_breaking():
    """Verify responder 4-level deterministic tie-breaking (D-05)."""
    id1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
    id2 = uuid.UUID("00000000-0000-0000-0000-000000000002")

    dummy_breakdown = ScoreBreakdown(skill=22.0, eta=25.0, fairness=15.0, reliability=10.0, credential_tier=10.0, radius_headroom=5.0)

    # Candidate A and B have same total score, but A has lower ETA
    cand_a = ScoredCandidate(
        rank=1,
        candidate_id=id2,
        full_name="Candidate A",
        category=ResponderCategory.NURSE,
        score_total=85.0,
        score_breakdown=dummy_breakdown,
        distance_m=1000.0,
        eta_s=180,
    )
    cand_b = ScoredCandidate(
        rank=1,
        candidate_id=id1,
        full_name="Candidate B",
        category=ResponderCategory.NURSE,
        score_total=85.0,
        score_breakdown=dummy_breakdown,
        distance_m=1200.0,
        eta_s=210,
    )

    ranked = rank_scored_responders([cand_b, cand_a])
    assert ranked[0].candidate_id == id2  # Lower ETA ranks first
    assert ranked[0].rank == 1
    assert ranked[1].candidate_id == id1
    assert ranked[1].rank == 2

    # If scores and ETA are identical, higher reliability breaks tie
    breakdown_high_rel = ScoreBreakdown(skill=22.0, eta=25.0, fairness=15.0, reliability=10.0, credential_tier=10.0, radius_headroom=5.0)
    breakdown_low_rel = ScoreBreakdown(skill=24.0, eta=25.0, fairness=15.0, reliability=8.0, credential_tier=10.0, radius_headroom=5.0)

    cand_c = ScoredCandidate(
        rank=1,
        candidate_id=id2,
        full_name="Candidate C",
        category=ResponderCategory.NURSE,
        score_total=87.0,
        score_breakdown=breakdown_low_rel,
        distance_m=1000.0,
        eta_s=180,
    )
    cand_d = ScoredCandidate(
        rank=1,
        candidate_id=id1,
        full_name="Candidate D",
        category=ResponderCategory.NURSE,
        score_total=87.0,
        score_breakdown=breakdown_high_rel,
        distance_m=1000.0,
        eta_s=180,
    )

    ranked2 = rank_scored_responders([cand_c, cand_d])
    assert ranked2[0].candidate_id == id1  # Higher reliability breaks tie
    assert ranked2[0].rank == 1


def test_rank_scored_ambulances_tie_breaking():
    """Verify ambulance 4-level deterministic tie-breaking."""
    id1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
    id2 = uuid.UUID("00000000-0000-0000-0000-000000000002")

    unit_a = ScoredAmbulance(
        rank=1,
        unit_id=id1,
        callsign="Amb-A",
        unit_type=AmbulanceUnitType.ADVANCED,
        score_total=90.0,
        score_breakdown=AmbulanceScoreBreakdown(eta=60.0, suitability=20.0, fairness=10.0),
        distance_m=2000.0,
        eta_s=250,
    )
    unit_b = ScoredAmbulance(
        rank=1,
        unit_id=id2,
        callsign="Amb-B",
        unit_type=AmbulanceUnitType.BASIC,
        score_total=80.0,
        score_breakdown=AmbulanceScoreBreakdown(eta=60.0, suitability=10.0, fairness=10.0),
        distance_m=2000.0,
        eta_s=250,
    )

    ranked = rank_scored_ambulances([unit_b, unit_a])
    assert ranked[0].callsign == "Amb-A"
    assert ranked[0].rank == 1
    assert ranked[1].callsign == "Amb-B"
    assert ranked[1].rank == 2
