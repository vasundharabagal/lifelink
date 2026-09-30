"""Database candidate loader service with SQL bounding-box spatial prefiltering (Spec §6.3, ORCH-01)."""
from typing import Optional, List, Set
import uuid
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload
from app.core.clock import Clock
from app.core.config import settings
from app.domain.enums import (
    Priority,
    EmergencyType,
    SkillCode,
    ResponderCategory,
    ResponderReadiness,
    CredentialStatus,
    AmbulanceUnitType,
    AmbulanceUnitStatus,
)
from app.models.user import User
from app.models.responder import ResponderProfile, ResponderSkill, ResponderCredential
from app.models.ambulance import AmbulanceUnit
from app.models.emergency import Emergency, DispatchOffer
from app.schemas.triage import RequiredSkill
from app.orchestration.distance import bounding_box_delta_deg
from app.orchestration.schemas import (
    CandidateProfile,
    CandidateSkill,
    CandidateCredential,
    AmbulanceCandidate,
    EmergencyContext,
    OrchestrationResult,
)
from app.orchestration.engine import orchestrate_matching


def find_and_rank_candidates(
    db: Session,
    emergency_id: uuid.UUID,
    clock: Clock,
    max_search_radius_m: int = 5000,
) -> OrchestrationResult:
    """Load nearby candidates from PostgreSQL with bounding-box prefilter, score, and rank."""
    # 1. Load emergency
    emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emergency:
        raise ValueError(f"Emergency with ID {emergency_id} not found")

    # 2. Extract active and handled candidates from dispatch_offers
    excluded_responders: Set[uuid.UUID] = set()
    active_responders: Set[uuid.UUID] = set()
    excluded_ambulances: Set[uuid.UUID] = set()
    active_ambulances: Set[uuid.UUID] = set()

    for offer in emergency.offers:
        if offer.target_kind == "responder" and offer.responder_id:
            if offer.status in ("OFFERED", "ACCEPTED", "ARRIVED"):
                active_responders.add(offer.responder_id)
            elif offer.status in ("DECLINED", "EXPIRED", "CANCELLED"):
                excluded_responders.add(offer.responder_id)
        elif offer.target_kind == "ambulance" and offer.ambulance_id:
            if offer.status in ("OFFERED", "ACCEPTED", "ARRIVED"):
                active_ambulances.add(offer.ambulance_id)
            elif offer.status in ("DECLINED", "EXPIRED", "CANCELLED"):
                excluded_ambulances.add(offer.ambulance_id)

    # 3. Parse required skills from triage JSON
    triage_data = emergency.triage or {}
    raw_req_skills = triage_data.get("required_skills", [])
    required_skills = [
        RequiredSkill(skill=SkillCode(s["skill"]), min_level=int(s["min_level"]))
        for s in raw_req_skills
    ]
    protocol_id = triage_data.get("protocol_id", "PROT_GENERAL")

    emergency_context = EmergencyContext(
        emergency_id=emergency.id,
        lat=emergency.lat,
        lng=emergency.lng,
        priority=Priority(emergency.priority),
        emergency_type=EmergencyType(emergency.emergency_type),
        protocol_id=protocol_id,
        required_skills=required_skills,
        patient_user_id=emergency.patient_user_id,
        reported_by_user_id=emergency.reported_by_user_id,
        demo_session_id=emergency.demo_session_id,
        excluded_responder_ids=excluded_responders,
        excluded_ambulance_ids=excluded_ambulances,
        active_responder_ids=active_responders,
        active_ambulance_ids=active_ambulances,
    )

    # 4. SQL Bounding-Box Spatial Prefilter
    lat_delta, lng_delta = bounding_box_delta_deg(max_search_radius_m, emergency.lat)
    min_lat = emergency.lat - lat_delta
    max_lat = emergency.lat + lat_delta
    min_lng = emergency.lng - lng_delta
    max_lng = emergency.lng + lng_delta

    # Fetch candidate profiles within bounding box OR with missing coordinates (for rejection reporting)
    responder_query = (
        select(ResponderProfile)
        .join(User, ResponderProfile.user_id == User.id)
        .options(
            selectinload(ResponderProfile.user).selectinload(User.skills),
            selectinload(ResponderProfile.user).selectinload(User.credentials),
        )
        .where(
            or_(
                # Within bounding box
                (
                    ResponderProfile.last_lat.between(min_lat, max_lat)
                    & ResponderProfile.last_lng.between(min_lng, max_lng)
                ),
                # Or location unknown (so it can be evaluated for rejection code)
                ResponderProfile.last_lat.is_(None),
                ResponderProfile.last_lng.is_(None),
            )
        )
    )

    if emergency.demo_session_id is not None:
        responder_query = responder_query.where(User.demo_session_id == emergency.demo_session_id)
    else:
        responder_query = responder_query.where(User.demo_session_id.is_(None))

    profiles: List[ResponderProfile] = db.execute(responder_query).scalars().all()

    candidate_profiles: List[CandidateProfile] = []
    for p in profiles:
        u = p.user
        cand_skills = [
            CandidateSkill(skill_code=SkillCode(s.skill_code), level=s.level)
            for s in u.skills
        ]
        cand_creds = [
            CandidateCredential(
                credential_type=c.credential_type,
                status=CredentialStatus(c.status),
                expires_on=c.expires_on,
            )
            for c in u.credentials
        ]
        candidate_profiles.append(
            CandidateProfile(
                user_id=p.user_id,
                full_name=u.full_name,
                category=ResponderCategory(p.category),
                is_active=u.is_active,
                readiness=ResponderReadiness(p.readiness),
                service_radius_m=p.service_radius_m,
                last_lat=p.last_lat,
                last_lng=p.last_lng,
                last_location_at=p.last_location_at,
                pinned_location=p.pinned_location,
                acceptance_rate=p.acceptance_rate,
                responses_24h=p.responses_24h,
                cooldown_until=p.cooldown_until,
                demo_session_id=u.demo_session_id,
                skills=cand_skills,
                credentials=cand_creds,
            )
        )

    # 5. Load Ambulance Units
    amb_query = select(AmbulanceUnit)
    if emergency.demo_session_id is not None:
        amb_query = amb_query.where(AmbulanceUnit.demo_session_id == emergency.demo_session_id)
    else:
        amb_query = amb_query.where(AmbulanceUnit.demo_session_id.is_(None))

    units: List[AmbulanceUnit] = db.execute(amb_query).scalars().all()
    ambulance_candidates: List[AmbulanceCandidate] = [
        AmbulanceCandidate(
            id=a.id,
            callsign=a.callsign,
            unit_type=AmbulanceUnitType(a.unit_type),
            status=AmbulanceUnitStatus(a.status),
            lat=a.lat,
            lng=a.lng,
            demo_session_id=a.demo_session_id,
        )
        for a in units
    ]

    # 6. Run pure matching engine
    return orchestrate_matching(
        candidates=candidate_profiles,
        ambulance_units=ambulance_candidates,
        emergency=emergency_context,
        clock=clock,
        config=settings,
    )
