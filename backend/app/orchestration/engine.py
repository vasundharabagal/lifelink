"""Pure in-memory response orchestration engine and explainability generator (Spec §6.4, §6.5, ORCH-03)."""
from typing import List, Tuple, Any, Dict
from app.core.clock import Clock
from app.core.config import Settings
from app.domain.enums import TrackKind, TargetKind
from app.orchestration.filters import (
    evaluate_responder_eligibility,
    evaluate_ambulance_eligibility,
)
from app.orchestration.scoring import (
    score_responder,
    score_ambulance,
    rank_scored_responders,
    rank_scored_ambulances,
)
from app.orchestration.schemas import (
    CandidateProfile,
    AmbulanceCandidate,
    EmergencyContext,
    ScoredCandidate,
    ScoredAmbulance,
    RejectionDetail,
    MatchExplanation,
    OrchestrationResult,
)


def build_citizen_summary(ranked: List[Any], track: TrackKind) -> str:
    """Generate a privacy-safe one-line status string for citizen UI (D-04, Spec §6.5).
    
    Protects responder identity and exact coordinates:
    Never exposes names, phone numbers, or exact coordinates.
    """
    if track == TrackKind.COMMUNITY:
        if not ranked:
            return "Searching for qualified community responders nearby..."
        top = ranked[0]
        # Format clean category label
        category_label = top.category.value.replace("_", " ")
        eta_min = max(1, round(top.eta_s / 60))
        return f"Contacting nearby {category_label} (~{eta_min} min ETA)"
    else:
        if not ranked:
            return "Contacting professional emergency medical services..."
        top = ranked[0]
        eta_min = max(1, round(top.eta_s / 60))
        unit_label = "advanced life support" if top.unit_type.value == "advanced" else "basic"
        return f"Dispatching {unit_label} emergency ambulance (~{eta_min} min ETA)"


def build_match_explanation(
    emergency: EmergencyContext,
    track: TrackKind,
    ranked: List[Any],
    rejected: List[RejectionDetail],
    clock: Clock,
    rules_version: str = "1.0.0",
) -> MatchExplanation:
    """Build a transparent MatchExplanation object for authority/demo oversight."""
    weights: Dict[str, float] = (
        {
            "skill": 30.0,
            "eta": 30.0,
            "fairness": 15.0,
            "reliability": 10.0,
            "credential_tier": 10.0,
            "radius_headroom": 5.0,
        }
        if track == TrackKind.COMMUNITY
        else {
            "eta": 70.0,
            "suitability": 20.0,
            "fairness": 10.0,
        }
    )

    ranked_dicts = [item.model_dump() for item in ranked]
    citizen_summary = build_citizen_summary(ranked, track)

    return MatchExplanation(
        emergency_id=emergency.emergency_id,
        track=track,
        computed_at=clock.now(),
        rules_version=rules_version,
        weights=weights,
        ranked=ranked_dicts,
        rejected=rejected,
        citizen_summary=citizen_summary,
    )


def filter_and_rank_responders(
    candidates: List[CandidateProfile],
    emergency: EmergencyContext,
    clock: Clock,
    config: Settings,
) -> Tuple[List[ScoredCandidate], List[RejectionDetail]]:
    """Filter candidate volunteers against hard gates, score eligible candidates, and rank deterministically."""
    eligible_scored: List[ScoredCandidate] = []
    rejected: List[RejectionDetail] = []

    for cand in candidates:
        rejection = evaluate_responder_eligibility(
            cand, emergency, clock, max_freshness_s=config.LOCATION_FRESHNESS_S
        )
        if rejection is not None:
            rejected.append(rejection)
        else:
            scored = score_responder(cand, emergency, clock, config)
            eligible_scored.append(scored)

    ranked = rank_scored_responders(eligible_scored)
    # Truncate to maximum community candidates allowed per plan (Spec §6.1)
    truncated_ranked = ranked[: config.MAX_COMMUNITY_CANDIDATES]

    return truncated_ranked, rejected


def filter_and_rank_ambulances(
    units: List[AmbulanceCandidate],
    emergency: EmergencyContext,
    clock: Clock,
    config: Settings,
) -> Tuple[List[ScoredAmbulance], List[RejectionDetail]]:
    """Filter ambulance units against hard gates, score eligible units, and rank deterministically."""
    eligible_scored: List[ScoredAmbulance] = []
    rejected: List[RejectionDetail] = []

    for unit in units:
        rejection = evaluate_ambulance_eligibility(unit, emergency, clock)
        if rejection is not None:
            rejected.append(rejection)
        else:
            scored = score_ambulance(unit, emergency, clock, config)
            eligible_scored.append(scored)

    ranked = rank_scored_ambulances(eligible_scored)
    # Truncate to maximum ambulance candidates allowed per plan (Spec §6.1)
    truncated_ranked = ranked[: config.MAX_AMBULANCE_CANDIDATES]

    return truncated_ranked, rejected


def orchestrate_matching(
    candidates: List[CandidateProfile],
    ambulance_units: List[AmbulanceCandidate],
    emergency: EmergencyContext,
    clock: Clock,
    config: Settings,
) -> OrchestrationResult:
    """Run pure response orchestration for both community and professional tracks."""
    now_dt = clock.now()

    # Community track
    ranked_responders, rejected_responders = filter_and_rank_responders(
        candidates, emergency, clock, config
    )
    community_explanation = build_match_explanation(
        emergency=emergency,
        track=TrackKind.COMMUNITY,
        ranked=ranked_responders,
        rejected=rejected_responders,
        clock=clock,
    )

    # Professional track
    ranked_ambulances, rejected_ambulances = filter_and_rank_ambulances(
        ambulance_units, emergency, clock, config
    )
    professional_explanation = build_match_explanation(
        emergency=emergency,
        track=TrackKind.PROFESSIONAL,
        ranked=ranked_ambulances,
        rejected=rejected_ambulances,
        clock=clock,
    )

    return OrchestrationResult(
        emergency_id=emergency.emergency_id,
        computed_at=now_dt,
        community_plan=ranked_responders,
        professional_plan=ranked_ambulances,
        community_explanation=community_explanation,
        professional_explanation=professional_explanation,
    )
