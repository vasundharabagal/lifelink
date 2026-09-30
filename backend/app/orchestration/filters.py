"""Hard eligibility filtering logic for community responders and ambulances (Spec §6.3, ORCH-01)."""
from typing import Optional, List
from app.core.clock import Clock
from app.domain.enums import (
    CredentialStatus,
    ResponderReadiness,
    AmbulanceUnitStatus,
    TargetKind,
    EligibilityRejectionReason,
    SkillCode,
)
from app.orchestration.distance import haversine_distance_m
from app.orchestration.schemas import (
    CandidateProfile,
    AmbulanceCandidate,
    EmergencyContext,
    RejectionDetail,
)


def evaluate_responder_eligibility(
    candidate: CandidateProfile,
    emergency: EmergencyContext,
    clock: Clock,
    max_freshness_s: int = 300,
) -> Optional[RejectionDetail]:
    """Evaluate volunteer responder against hard eligibility gates.
    
    Any failure adds machine-readable reason codes and returns a RejectionDetail.
    If all hard gates pass, returns None (candidate is eligible for scoring).
    """
    reasons: List[EligibilityRejectionReason] = []
    dist_m: Optional[float] = None
    now_dt = clock.now()
    today_date = now_dt.date()

    # 1. Scope mismatch (tenant isolation)
    if candidate.demo_session_id != emergency.demo_session_id:
        reasons.append(EligibilityRejectionReason.SCOPE_MISMATCH)

    # 2. Conflict of interest: responder cannot be the patient or reporter
    if candidate.user_id in (emergency.patient_user_id, emergency.reported_by_user_id):
        reasons.append(EligibilityRejectionReason.IS_PATIENT)

    # 3. Account active check
    if not candidate.is_active:
        reasons.append(EligibilityRejectionReason.ACCOUNT_INACTIVE)

    # 4. Readiness & cooldown check
    if candidate.readiness != ResponderReadiness.AVAILABLE:
        reasons.append(EligibilityRejectionReason.NOT_AVAILABLE)
    elif candidate.cooldown_until is not None and candidate.cooldown_until > now_dt:
        reasons.append(EligibilityRejectionReason.NOT_AVAILABLE)

    # 5. Active assignment check
    if candidate.user_id in emergency.active_responder_ids:
        reasons.append(EligibilityRejectionReason.ACTIVE_ASSIGNMENT)

    # 6. Already handled (declined, expired, cancelled) for this incident
    if candidate.user_id in emergency.excluded_responder_ids:
        reasons.append(EligibilityRejectionReason.ALREADY_DECLINED_OR_EXPIRED)

    # 7. Credential verification gate: must have at least one verified, non-expired credential
    has_valid_credential = any(
        cred.status == CredentialStatus.VERIFIED and cred.expires_on >= today_date
        for cred in candidate.credentials
    )
    if not has_valid_credential:
        reasons.append(EligibilityRejectionReason.NOT_VERIFIED)

    # 8. Location unknown check
    if candidate.last_lat is None or candidate.last_lng is None:
        reasons.append(EligibilityRejectionReason.LOCATION_UNKNOWN)
    else:
        # 9. Location freshness check (bypassed if pinned_location is True)
        if not candidate.pinned_location:
            if candidate.last_location_at is None:
                reasons.append(EligibilityRejectionReason.LOCATION_STALE)
            else:
                elapsed_s = (now_dt - candidate.last_location_at).total_seconds()
                if elapsed_s > max_freshness_s:
                    reasons.append(EligibilityRejectionReason.LOCATION_STALE)

        # 10. Service radius check
        dist_m = haversine_distance_m(
            candidate.last_lat, candidate.last_lng, emergency.lat, emergency.lng
        )
        if dist_m > candidate.service_radius_m:
            reasons.append(EligibilityRejectionReason.OUTSIDE_SERVICE_RADIUS)

    # 11. Skill compatibility check
    if emergency.required_skills:
        # Candidate satisfies requirements if any required skill is matched at or above min_level,
        # or if candidate holds Advanced Life Support Level 3
        has_matching_skill = False
        cand_skill_map = {s.skill_code: s.level for s in candidate.skills}

        # Check for ALS level 3 wildcard proficiency
        if cand_skill_map.get(SkillCode.ADVANCED_LIFE_SUPPORT, 0) >= 3:
            has_matching_skill = True
        else:
            for req in emergency.required_skills:
                held_level = cand_skill_map.get(req.skill, 0)
                if held_level >= req.min_level:
                    has_matching_skill = True
                    break

        if not has_matching_skill:
            reasons.append(EligibilityRejectionReason.SKILL_MISMATCH)

    if not reasons:
        return None

    # Construct plain-language summary
    summary_parts = []
    if EligibilityRejectionReason.SCOPE_MISMATCH in reasons:
        summary_parts.append("Scope mismatch between demo session and incident")
    if EligibilityRejectionReason.IS_PATIENT in reasons:
        summary_parts.append("Responder is patient or reporter")
    if EligibilityRejectionReason.ACCOUNT_INACTIVE in reasons:
        summary_parts.append("Responder account is inactive")
    if EligibilityRejectionReason.NOT_AVAILABLE in reasons:
        summary_parts.append(f"Responder readiness is '{candidate.readiness.value}'")
    if EligibilityRejectionReason.ACTIVE_ASSIGNMENT in reasons:
        summary_parts.append("Responder has an active emergency assignment")
    if EligibilityRejectionReason.ALREADY_DECLINED_OR_EXPIRED in reasons:
        summary_parts.append("Responder already declined or timed out for this incident")
    if EligibilityRejectionReason.NOT_VERIFIED in reasons:
        summary_parts.append("Responder credentials are not verified or expired")
    if EligibilityRejectionReason.LOCATION_UNKNOWN in reasons:
        summary_parts.append("Responder location coordinates are missing")
    if EligibilityRejectionReason.LOCATION_STALE in reasons:
        summary_parts.append("Responder location coordinates are stale (>300s)")
    if EligibilityRejectionReason.OUTSIDE_SERVICE_RADIUS in reasons and dist_m is not None:
        summary_parts.append(
            f"Distance ({round(dist_m / 1000.0, 1)} km) exceeds service radius ({round(candidate.service_radius_m / 1000.0, 1)} km)"
        )
    if EligibilityRejectionReason.SKILL_MISMATCH in reasons:
        req_names = ", ".join(f"{r.skill.value}>={r.min_level}" for r in emergency.required_skills)
        summary_parts.append(f"Lacks required skills for protocol ({req_names})")

    return RejectionDetail(
        candidate_id=candidate.user_id,
        target_kind=TargetKind.RESPONDER,
        name_or_callsign=candidate.full_name,
        reason_codes=reasons,
        summary="; ".join(summary_parts) if summary_parts else "Ineligible for dispatch",
        distance_m=dist_m,
    )


def evaluate_ambulance_eligibility(
    unit: AmbulanceCandidate,
    emergency: EmergencyContext,
    clock: Clock,
) -> Optional[RejectionDetail]:
    """Evaluate professional ambulance unit against hard eligibility gates.
    
    Any failure adds machine-readable reason codes and returns a RejectionDetail.
    If all hard gates pass, returns None.
    """
    reasons: List[EligibilityRejectionReason] = []
    dist_m = haversine_distance_m(unit.lat, unit.lng, emergency.lat, emergency.lng)

    # 1. Scope mismatch
    if unit.demo_session_id != emergency.demo_session_id:
        reasons.append(EligibilityRejectionReason.SCOPE_MISMATCH)

    # 2. Availability status
    if unit.status != AmbulanceUnitStatus.AVAILABLE:
        reasons.append(EligibilityRejectionReason.UNIT_NOT_AVAILABLE)

    # 3. Active assignment
    if unit.id in emergency.active_ambulance_ids:
        reasons.append(EligibilityRejectionReason.ACTIVE_ASSIGNMENT)

    # 4. Already declined / expired
    if unit.id in emergency.excluded_ambulance_ids:
        reasons.append(EligibilityRejectionReason.ALREADY_DECLINED_OR_EXPIRED)

    if not reasons:
        return None

    summary_parts = []
    if EligibilityRejectionReason.SCOPE_MISMATCH in reasons:
        summary_parts.append("Scope mismatch between demo session and incident")
    if EligibilityRejectionReason.UNIT_NOT_AVAILABLE in reasons:
        summary_parts.append(f"Unit status is '{unit.status.value}'")
    if EligibilityRejectionReason.ACTIVE_ASSIGNMENT in reasons:
        summary_parts.append("Unit currently assigned to another emergency")
    if EligibilityRejectionReason.ALREADY_DECLINED_OR_EXPIRED in reasons:
        summary_parts.append("Unit already declined or expired for this incident")

    return RejectionDetail(
        candidate_id=unit.id,
        target_kind=TargetKind.AMBULANCE,
        name_or_callsign=unit.callsign,
        reason_codes=reasons,
        summary="; ".join(summary_parts) if summary_parts else "Ineligible ambulance unit",
        distance_m=dist_m,
    )
