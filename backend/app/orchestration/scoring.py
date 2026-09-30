"""Multi-factor scoring algorithms and deterministic tie-breaking for LIFELINK (Spec §6.4, ORCH-02, ORCH-04)."""
from typing import List, Dict, Optional
from app.core.clock import Clock
from app.core.config import Settings
from app.domain.enums import (
    ResponderCategory,
    AmbulanceUnitType,
    Priority,
    EmergencyType,
    SkillCode,
)
from app.schemas.triage import RequiredSkill
from app.orchestration.distance import haversine_distance_m, calculate_eta_seconds
from app.orchestration.schemas import (
    CandidateProfile,
    CandidateSkill,
    AmbulanceCandidate,
    EmergencyContext,
    ScoreBreakdown,
    AmbulanceScoreBreakdown,
    ScoredCandidate,
    ScoredAmbulance,
)


def calculate_skill_score(
    candidate_skills: List[CandidateSkill],
    required_skills: List[RequiredSkill],
    emergency_type: EmergencyType,
) -> float:
    """Calculate skill score out of 30.0 points.
    
    Formula (D-01):
        - Base 22.0 points for meeting minimum required skill level.
        - +4.0 points per surplus skill level above requirement.
        - +2.0 points per relevant secondary skill held.
        - Hard-capped at 30.0 points total.
    """
    if not required_skills:
        return 30.0

    cand_skills_map: Dict[SkillCode, int] = {s.skill_code: s.level for s in candidate_skills}

    # Check for Advanced Life Support level 3 proficiency wildcard
    has_als_wildcard = cand_skills_map.get(SkillCode.ADVANCED_LIFE_SUPPORT, 0) >= 3

    # Find highest base + surplus across required skills
    best_base = 0.0
    best_surplus = 0.0
    matched_skills = set()

    for req in required_skills:
        held_level = cand_skills_map.get(req.skill, 0)
        if held_level >= req.min_level:
            base = 22.0
            surplus = (held_level - req.min_level) * 4.0
            matched_skills.add(req.skill)
            if (base + surplus) > (best_base + best_surplus):
                best_base = base
                best_surplus = surplus
        elif has_als_wildcard:
            # ALS wildcard counts as full match
            base = 22.0
            surplus = 4.0  # equivalent to Level 3 surplus
            matched_skills.add(req.skill)
            if (base + surplus) > (best_base + best_surplus):
                best_base = base
                best_surplus = surplus

    # Secondary bonus for additional relevant skills held
    secondary_skills = [
        s for s in candidate_skills if s.skill_code not in matched_skills
    ]
    secondary_bonus = len(secondary_skills) * 2.0

    total_skill_score = min(30.0, best_base + best_surplus + secondary_bonus)
    return round(total_skill_score, 1)


def calculate_eta_score(eta_s: int, eta_cap_s: int = 900) -> float:
    """Calculate community responder ETA score out of 30.0 points.
    
    Formula: 30.0 * max(0.0, 1.0 - (eta_s / eta_cap_s))
    """
    if eta_s <= 0:
        return 30.0
    normalized = max(0.0, 1.0 - (eta_s / float(eta_cap_s)))
    return round(30.0 * normalized, 1)


def calculate_fairness_score(responses_24h: int, max_responses: float = 5.0) -> float:
    """Calculate fairness score out of 15.0 points to prevent volunteer burnout.
    
    Formula: 15.0 * max(0.0, 1.0 - (responses_24h / max_responses))
    """
    if responses_24h <= 0:
        return 15.0
    normalized = max(0.0, 1.0 - (responses_24h / float(max_responses)))
    return round(15.0 * normalized, 1)


def calculate_reliability_score(acceptance_rate: float) -> float:
    """Calculate reliability score out of 10.0 points based on historical acceptance.
    
    Formula: 10.0 * clamp(acceptance_rate, 0.0, 1.0)
    """
    clamped = max(0.0, min(1.0, acceptance_rate))
    return round(10.0 * clamped, 1)


def calculate_credential_tier_score(category: ResponderCategory) -> float:
    """Calculate credential tier score out of 10.0 points.
    
    Tiers (Spec §6.4):
        - Professional (doctor, nurse, paramedic): 10.0
        - Certified (emt, certified_first_aider): 7.0
        - Trained (medical_volunteer, student_responder): 4.0
        - Other: 2.0
    """
    if category in (ResponderCategory.DOCTOR, ResponderCategory.NURSE, ResponderCategory.PARAMEDIC):
        return 10.0
    if category in (ResponderCategory.EMT, ResponderCategory.CERTIFIED_FIRST_AIDER):
        return 7.0
    if category in (ResponderCategory.MEDICAL_VOLUNTEER, ResponderCategory.STUDENT_RESPONDER):
        return 4.0
    return 2.0


def calculate_radius_headroom_score(distance_m: float, service_radius_m: int) -> float:
    """Calculate radius headroom score out of 5.0 points (D-07).
    
    Formula:
        ratio = distance_m / service_radius_m
        If ratio <= 0.5: 5.0 points
        If 0.5 < ratio <= 1.0: 10.0 * (1.0 - ratio)
        Else: 0.0 points
    """
    if service_radius_m <= 0 or distance_m < 0:
        return 0.0

    ratio = distance_m / float(service_radius_m)
    if ratio <= 0.5:
        return 5.0
    if ratio <= 1.0:
        return round(10.0 * (1.0 - ratio), 1)
    return 0.0


def score_responder(
    candidate: CandidateProfile,
    emergency: EmergencyContext,
    clock: Clock,
    config: Settings,
) -> ScoredCandidate:
    """Calculate complete multi-factor score (0-100) and explanations for an eligible responder."""
    lat = candidate.last_lat or emergency.lat
    lng = candidate.last_lng or emergency.lng
    dist_m = haversine_distance_m(lat, lng, emergency.lat, emergency.lng)
    eta_s = calculate_eta_seconds(
        dist_m,
        speed_kmh=config.RESPONDER_SPEED_KMH,
        detour_factor=config.DETOUR_FACTOR,
        min_seconds=30,
    )

    skill_score = calculate_skill_score(candidate.skills, emergency.required_skills, emergency.emergency_type)
    eta_score = calculate_eta_score(eta_s, config.ETA_CAP_S)
    fairness_score = calculate_fairness_score(candidate.responses_24h)
    reliability_score = calculate_reliability_score(candidate.acceptance_rate)
    tier_score = calculate_credential_tier_score(candidate.category)
    headroom_score = calculate_radius_headroom_score(dist_m, candidate.service_radius_m)

    total_score = round(
        min(100.0, skill_score + eta_score + fairness_score + reliability_score + tier_score + headroom_score),
        1,
    )

    breakdown = ScoreBreakdown(
        skill=skill_score,
        eta=eta_score,
        fairness=fairness_score,
        reliability=reliability_score,
        credential_tier=tier_score,
        radius_headroom=headroom_score,
    )

    # Human-readable reasons and caveats
    reasons = [
        f"Verified {candidate.category.value.replace('_', ' ').title()}",
        f"Available ({round(dist_m / 1000.0, 1)} km away)",
        f"Estimated arrival in ~{max(1, round(eta_s / 60))} min",
    ]
    if skill_score >= 26.0:
        reasons.append("High skill proficiency for protocol")

    caveats = []
    if candidate.responses_24h >= 3:
        caveats.append(f"High 24h response volume ({candidate.responses_24h} responses)")
    if dist_m > (candidate.service_radius_m * 0.8):
        caveats.append("Near service radius boundary")
    caveats.append("ETA is estimated based on assumed 25 km/h urban travel")

    return ScoredCandidate(
        rank=1,
        candidate_id=candidate.user_id,
        full_name=candidate.full_name,
        category=candidate.category,
        score_total=total_score,
        score_breakdown=breakdown,
        distance_m=dist_m,
        eta_s=eta_s,
        reasons=reasons,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Ambulance Unit Scoring
# ---------------------------------------------------------------------------

def calculate_ambulance_suitability_score(unit_type: AmbulanceUnitType, priority: Priority) -> float:
    """Calculate ambulance unit suitability score out of 20.0 points (D-02).
    
    Formula:
        - For P1 emergencies:
            - Advanced Life Support (ALS): 20.0 points
            - Basic Life Support (BLS): 10.0 points
        - For P2 / P3 emergencies:
            - Basic Life Support (BLS): 20.0 points
            - Advanced Life Support (ALS): 15.0 points (preserves ALS units for cardiac arrest)
    """
    if priority == Priority.P1_CRITICAL:
        if unit_type == AmbulanceUnitType.ADVANCED:
            return 20.0
        return 10.0
    else:
        if unit_type == AmbulanceUnitType.BASIC:
            return 20.0
        return 15.0


def calculate_ambulance_eta_score(eta_s: int, eta_cap_s: int = 900) -> float:
    """Calculate professional ambulance ETA score out of 70.0 points.
    
    Formula: 70.0 * max(0.0, 1.0 - (eta_s / eta_cap_s))
    """
    if eta_s <= 0:
        return 70.0
    normalized = max(0.0, 1.0 - (eta_s / float(eta_cap_s)))
    return round(70.0 * normalized, 1)


def calculate_ambulance_fairness_score(runs_24h: int, max_runs: float = 5.0) -> float:
    """Calculate ambulance fairness score out of 10.0 points.
    
    Formula: 10.0 * max(0.0, 1.0 - (runs_24h / max_runs))
    """
    if runs_24h <= 0:
        return 10.0
    normalized = max(0.0, 1.0 - (runs_24h / float(max_runs)))
    return round(10.0 * normalized, 1)


def score_ambulance(
    unit: AmbulanceCandidate,
    emergency: EmergencyContext,
    clock: Clock,
    config: Settings,
) -> ScoredAmbulance:
    """Calculate multi-factor score (0-100) and explanations for an eligible ambulance unit."""
    dist_m = haversine_distance_m(unit.lat, unit.lng, emergency.lat, emergency.lng)
    eta_s = calculate_eta_seconds(
        dist_m,
        speed_kmh=config.AMBULANCE_SPEED_KMH,
        detour_factor=config.DETOUR_FACTOR,
        min_seconds=30,
    )

    eta_score = calculate_ambulance_eta_score(eta_s, config.ETA_CAP_S)
    suitability_score = calculate_ambulance_suitability_score(unit.unit_type, emergency.priority)
    fairness_score = calculate_ambulance_fairness_score(unit.runs_24h)

    total_score = round(min(100.0, eta_score + suitability_score + fairness_score), 1)

    breakdown = AmbulanceScoreBreakdown(
        eta=eta_score,
        suitability=suitability_score,
        fairness=fairness_score,
    )

    reasons = [
        f"Available {unit.unit_type.value.upper()} ambulance unit ({unit.callsign})",
        f"Estimated arrival in ~{max(1, round(eta_s / 60))} min ({round(dist_m / 1000.0, 1)} km)",
    ]
    if suitability_score == 20.0:
        reasons.append("Optimal equipment configuration for emergency priority")

    caveats = ["Ambulance travel time is estimated based on assumed 35 km/h urban speed"]

    return ScoredAmbulance(
        rank=1,
        unit_id=unit.id,
        callsign=unit.callsign,
        unit_type=unit.unit_type,
        score_total=total_score,
        score_breakdown=breakdown,
        distance_m=dist_m,
        eta_s=eta_s,
        reasons=reasons,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Deterministic Tie-Breaking
# ---------------------------------------------------------------------------

def rank_scored_responders(scored: List[ScoredCandidate]) -> List[ScoredCandidate]:
    """Deterministically sort and rank eligible scored responders (D-05, Spec §6.4).
    
    Tie-breaking hierarchy:
        1. Total score DESC
        2. ETA seconds ASC
        3. Reliability score DESC
        4. Candidate ID string ASC
    """
    sorted_candidates = sorted(
        scored,
        key=lambda c: (
            -c.score_total,
            c.eta_s,
            -c.score_breakdown.reliability,
            str(c.candidate_id),
        ),
    )

    ranked_result: List[ScoredCandidate] = []
    for idx, cand in enumerate(sorted_candidates, start=1):
        # Update rank attribute sequentially
        cand_dict = cand.model_dump()
        cand_dict["rank"] = idx
        ranked_result.append(ScoredCandidate(**cand_dict))

    return ranked_result


def rank_scored_ambulances(scored: List[ScoredAmbulance]) -> List[ScoredAmbulance]:
    """Deterministically sort and rank eligible scored ambulance units (Spec §6.4).
    
    Tie-breaking hierarchy:
        1. Total score DESC
        2. ETA seconds ASC
        3. Suitability score DESC
        4. Unit ID string ASC
    """
    sorted_units = sorted(
        scored,
        key=lambda a: (
            -a.score_total,
            a.eta_s,
            -a.score_breakdown.suitability,
            str(a.unit_id),
        ),
    )

    ranked_result: List[ScoredAmbulance] = []
    for idx, unit in enumerate(sorted_units, start=1):
        unit_dict = unit.model_dump()
        unit_dict["rank"] = idx
        ranked_result.append(ScoredAmbulance(**unit_dict))

    return ranked_result
