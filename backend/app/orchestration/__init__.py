"""LIFELINK Response Orchestration Engine package."""
from app.orchestration.distance import (
    haversine_distance_m,
    calculate_eta_seconds,
    bounding_box_delta_deg,
)
from app.orchestration.schemas import (
    CandidateProfile,
    CandidateSkill,
    CandidateCredential,
    AmbulanceCandidate,
    EmergencyContext,
    ScoreBreakdown,
    AmbulanceScoreBreakdown,
    ScoredCandidate,
    ScoredAmbulance,
    RejectionDetail,
    MatchExplanation,
    OrchestrationResult,
)
from app.orchestration.filters import (
    evaluate_responder_eligibility,
    evaluate_ambulance_eligibility,
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
from app.orchestration.engine import (
    build_citizen_summary,
    build_match_explanation,
    filter_and_rank_responders,
    filter_and_rank_ambulances,
    orchestrate_matching,
)
from app.orchestration.service import find_and_rank_candidates

__all__ = [
    # Distance & spatial math
    "haversine_distance_m",
    "calculate_eta_seconds",
    "bounding_box_delta_deg",
    # Schemas
    "CandidateProfile",
    "CandidateSkill",
    "CandidateCredential",
    "AmbulanceCandidate",
    "EmergencyContext",
    "ScoreBreakdown",
    "AmbulanceScoreBreakdown",
    "ScoredCandidate",
    "ScoredAmbulance",
    "RejectionDetail",
    "MatchExplanation",
    "OrchestrationResult",
    # Filters & scoring
    "evaluate_responder_eligibility",
    "evaluate_ambulance_eligibility",
    "calculate_skill_score",
    "calculate_eta_score",
    "calculate_fairness_score",
    "calculate_reliability_score",
    "calculate_credential_tier_score",
    "calculate_radius_headroom_score",
    "calculate_ambulance_suitability_score",
    "calculate_ambulance_eta_score",
    "calculate_ambulance_fairness_score",
    "score_responder",
    "score_ambulance",
    "rank_scored_responders",
    "rank_scored_ambulances",
    # Engine & Service
    "build_citizen_summary",
    "build_match_explanation",
    "filter_and_rank_responders",
    "filter_and_rank_ambulances",
    "orchestrate_matching",
    "find_and_rank_candidates",
]
