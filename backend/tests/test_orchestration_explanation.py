"""Unit tests for MatchExplanation generation and citizen summary privacy (ORCH-03)."""
import uuid
import pytest
from app.core.clock import Clock
from app.core.config import Settings
from app.domain.enums import (
    ResponderCategory,
    ResponderReadiness,
    CredentialStatus,
    Priority,
    EmergencyType,
    SkillCode,
    TrackKind,
    TargetKind,
    EligibilityRejectionReason,
)
from app.schemas.triage import RequiredSkill
from app.orchestration.schemas import (
    CandidateProfile,
    CandidateSkill,
    CandidateCredential,
    EmergencyContext,
    RejectionDetail,
)
from app.orchestration.engine import (
    build_citizen_summary,
    build_match_explanation,
    filter_and_rank_responders,
)


@pytest.fixture
def test_clock():
    return Clock()


@pytest.fixture
def config():
    return Settings()


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


def test_citizen_summary_privacy_no_pii(test_clock, config, emergency):
    """Citizen summary must never expose responder name, phone, or exact coordinates."""
    cand = CandidateProfile(
        user_id=uuid.uuid4(),
        full_name="Secret Name 123",
        category=ResponderCategory.NURSE,
        is_active=True,
        readiness=ResponderReadiness.AVAILABLE,
        service_radius_m=3000,
        last_lat=18.5255,
        last_lng=73.8620,
        last_location_at=test_clock.now(),
        skills=[CandidateSkill(skill_code=SkillCode.BLEEDING_CONTROL, level=3)],
        credentials=[
            CandidateCredential(
                credential_type="Nursing License",
                status=CredentialStatus.VERIFIED,
                expires_on=test_clock.now().date(),
            )
        ],
    )

    ranked, _ = filter_and_rank_responders([cand], emergency, test_clock, config)
    summary = build_citizen_summary(ranked, TrackKind.COMMUNITY)

    # Check privacy: no name, no coordinates, only generic role and ETA
    assert "Secret Name" not in summary
    assert "18.52" not in summary
    assert "73.86" not in summary
    assert "nurse" in summary.lower()
    assert "ETA" in summary


def test_citizen_summary_fallback_empty():
    """Empty candidate list yields reassuring fallback text."""
    community_empty = build_citizen_summary([], TrackKind.COMMUNITY)
    assert "Searching for qualified community responders" in community_empty

    ambulance_empty = build_citizen_summary([], TrackKind.PROFESSIONAL)
    assert "Contacting professional emergency" in ambulance_empty


def test_match_explanation_structure_and_weights(test_clock, config, emergency):
    """MatchExplanation contains weights, ranked dictionaries, and rejected lists."""
    explanation = build_match_explanation(
        emergency=emergency,
        track=TrackKind.COMMUNITY,
        ranked=[],
        rejected=[
            RejectionDetail(
                candidate_id=uuid.uuid4(),
                target_kind=TargetKind.RESPONDER,
                name_or_callsign="Karan",
                reason_codes=[EligibilityRejectionReason.SKILL_MISMATCH],
                summary="Lacks required skill",
            )
        ],
        clock=test_clock,
    )

    assert explanation.weights["skill"] == 30.0
    assert explanation.weights["eta"] == 30.0
    assert len(explanation.rejected) == 1
    assert explanation.rejected[0].reason_codes == [EligibilityRejectionReason.SKILL_MISMATCH]
    assert "Searching for qualified" in explanation.citizen_summary


def test_truncation_to_max_candidates(test_clock, config, emergency):
    """Engine truncates ranked responders to MAX_COMMUNITY_CANDIDATES (default 5)."""
    candidates = []
    for i in range(10):
        c = CandidateProfile(
            user_id=uuid.uuid4(),
            full_name=f"Responder {i}",
            category=ResponderCategory.NURSE,
            is_active=True,
            readiness=ResponderReadiness.AVAILABLE,
            service_radius_m=3000,
            last_lat=18.5204 + (i * 0.001),
            last_lng=73.8567,
            last_location_at=test_clock.now(),
            skills=[CandidateSkill(skill_code=SkillCode.BLEEDING_CONTROL, level=3)],
            credentials=[
                CandidateCredential(
                    credential_type="License",
                    status=CredentialStatus.VERIFIED,
                    expires_on=test_clock.now().date(),
                )
            ],
        )
        candidates.append(c)

    ranked, rejected = filter_and_rank_responders(candidates, emergency, test_clock, config)
    assert len(ranked) == config.MAX_COMMUNITY_CANDIDATES
    assert len(rejected) == 0
