"""Emergency lifecycle service: creation, deduplication, triage, and offer dispatch (Spec §5, §7.1)."""
from datetime import timedelta
from typing import Optional
import uuid
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.clock import Clock
from app.core.config import settings
from app.domain.enums import (
    EmergencyStatus,
    OfferStatus,
    Priority,
    TrackStatus,
    UserRole,
)
from app.models.emergency import DispatchOffer, Emergency, EmergencyEvent
from app.models.user import User
from app.orchestration.distance import bounding_box_delta_deg, haversine_distance_m
from app.orchestration.service import find_and_rank_candidates
from app.schemas.emergency import DuplicateEmergencyErrorResponse, EmergencyCreateRequest
from app.triage.rules import evaluate_rules


class DuplicateEmergencyError(Exception):
    """Raised when an active emergency exists within 150m and 10min (Spec §7.1)."""
    def __init__(self, detail: DuplicateEmergencyErrorResponse):
        super().__init__(detail.message)
        self.detail = detail


def create_emergency(
    db: Session,
    payload: EmergencyCreateRequest,
    reporter_user: User,
    clock: Clock,
    idempotency_key: str,
) -> tuple[Emergency, bool]:
    """Create a new emergency incident with idempotency replay, 150m deduplication, and initial dispatch.
    
    If the same (reporter_user_id, idempotency_key) exists, returns (existing_incident, True).
    If a new incident is created, returns (new_incident, False).
    If an active incident exists within 150m and 10min and force_create is False, raises DuplicateEmergencyError.
    """
    # 1. Idempotent key replay check (Spec §7.1)
    existing_idempotent = (
        db.query(Emergency)
        .options(selectinload(Emergency.events), selectinload(Emergency.offers))
        .filter(
            Emergency.reported_by_user_id == reporter_user.id,
            Emergency.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing_idempotent is not None:
        return existing_idempotent, True

    # 2. Near-simultaneous spatial deduplication check (150m, 10 min) (Spec §7.1)
    if not payload.force_create:
        ten_minutes_ago = clock.now() - timedelta(minutes=10)
        delta_lat, delta_lng = bounding_box_delta_deg(150.0, payload.lat)

        dedup_query = db.query(Emergency).filter(
            Emergency.status.notin_([
                EmergencyStatus.COMPLETED.value,
                EmergencyStatus.CANCELLED.value,
                EmergencyStatus.NO_COVERAGE_CLOSED.value,
            ]),
            Emergency.created_at >= ten_minutes_ago,
            Emergency.lat.between(payload.lat - delta_lat, payload.lat + delta_lat),
            Emergency.lng.between(payload.lng - delta_lng, payload.lng + delta_lng),
        )

        if payload.demo_session_id is not None:
            dedup_query = dedup_query.filter(Emergency.demo_session_id == payload.demo_session_id)
        else:
            dedup_query = dedup_query.filter(Emergency.demo_session_id.is_(None))

        candidates = dedup_query.all()
        for candidate in candidates:
            dist_m = haversine_distance_m(payload.lat, payload.lng, candidate.lat, candidate.lng)
            if dist_m <= 150.0:
                raise DuplicateEmergencyError(
                    DuplicateEmergencyErrorResponse(
                        error="POSSIBLE_DUPLICATE",
                        message=f"A near-simultaneous emergency was reported {int(dist_m)}m away within the last 10 minutes.",
                        existing_emergency_id=candidate.id,
                        distance_m=round(dist_m, 1),
                        priority=candidate.priority,
                        created_at=candidate.created_at,
                        can_force_create=True,
                    )
                )

    # 3. Triage classification (Spec §5.2, §5.4)
    triage_result = evaluate_rules(payload.triage_input)
    priority = triage_result.priority.value
    emergency_type = triage_result.emergency_type.value
    protocol_id = triage_result.protocol_id.value
    requires_ambulance = triage_result.ambulance_required

    # Determine track initial states
    if priority in (Priority.P1_CRITICAL.value, Priority.P2_SERIOUS.value):
        community_track = TrackStatus.SEARCHING.value
    else:
        community_track = TrackStatus.NOT_STARTED.value

    if requires_ambulance:
        professional_track = TrackStatus.SEARCHING.value
    else:
        professional_track = TrackStatus.NOT_STARTED.value

    patient_user_id = reporter_user.id

    now = clock.now()

    # 4. Create Emergency record
    emergency = Emergency(
        reported_by_user_id=reporter_user.id,
        patient_user_id=patient_user_id,
        idempotency_key=idempotency_key,
        status=EmergencyStatus.CREATED.value,
        community_track=community_track,
        professional_track=professional_track,
        priority=priority,
        emergency_type=emergency_type,
        triage=triage_result.model_dump(mode="json"),
        dispatch_plan={},
        lat=payload.lat,
        lng=payload.lng,
        location_accuracy_m=payload.location_accuracy_m,
        location_hint=payload.location_hint,
        patient_is_reporter=payload.patient_is_reporter,
        consent_share_medical=payload.consent_share_medical,
        version=1,
        next_event_seq=1,
        demo_session_id=payload.demo_session_id,
        created_at=now,
        updated_at=now,
    )
    db.add(emergency)
    db.flush()

    # 5. Append initial timeline events
    event_created = EmergencyEvent(
        emergency_id=emergency.id,
        seq=1,
        type="EMERGENCY_CREATED",
        actor_user_id=reporter_user.id,
        actor_role=reporter_user.role,
        payload={
            "emergency_type": emergency_type,
            "priority": priority,
            "patient_is_reporter": payload.patient_is_reporter,
        },
        visible_to=["citizen", "responder", "ambulance", "authority"],
        at=now,
    )
    db.add(event_created)

    event_triage = EmergencyEvent(
        emergency_id=emergency.id,
        seq=2,
        type="TRIAGE_COMPLETED",
        actor_user_id=None,
        actor_role="system",
        payload={
            "priority": priority,
            "protocol_id": protocol_id,
            "ambulance_required": requires_ambulance,
            "red_flags": [rf.value for rf in triage_result.red_flags],
        },
        visible_to=["citizen", "responder", "ambulance", "authority"],
        at=now,
    )
    db.add(event_triage)
    emergency.next_event_seq = 3
    emergency.status = EmergencyStatus.DISPATCHING.value

    # 6. Compile candidate dispatch plan via orchestration engine (Spec §6)
    orch_result = find_and_rank_candidates(db, emergency.id, clock, max_search_radius_m=5000)
    emergency.dispatch_plan = orch_result.model_dump(mode="json")

    # 7. Create initial dispatch offers
    # Community track offer
    if orch_result.community_plan and community_track == TrackStatus.SEARCHING.value:
        top_responder = orch_result.community_plan[0]
        offer_ttl = settings.OFFER_TTL_S
        community_offer = DispatchOffer(
            emergency_id=emergency.id,
            track="community",
            target_kind="responder",
            responder_id=top_responder.candidate_id,
            rank=1,
            status=OfferStatus.OFFERED.value,
            offered_at=now,
            expires_at=now + timedelta(seconds=offer_ttl),
            eta_s=top_responder.eta_s,
            distance_m=top_responder.distance_m,
            score_snapshot=top_responder.score_breakdown.model_dump(mode="json"),
        )
        db.add(community_offer)
        emergency.community_track = TrackStatus.OFFERED.value

        event_offer = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="OFFER_CREATED",
            actor_user_id=None,
            actor_role="system",
            payload={
                "track": "community",
                "responder_id": str(top_responder.candidate_id),
                "rank": 1,
                "eta_s": top_responder.eta_s,
                "expires_at": community_offer.expires_at.isoformat(),
            },
            visible_to=["citizen", "responder", "ambulance", "authority"],
            at=now,
        )
        db.add(event_offer)
        emergency.next_event_seq += 1
    elif community_track == TrackStatus.SEARCHING.value:
        emergency.community_track = TrackStatus.UNAVAILABLE.value
        event_exhausted = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="TRACK_EXHAUSTED",
            actor_user_id=None,
            actor_role="system",
            payload={"track": "community", "reason": "No eligible community responders nearby"},
            visible_to=["citizen", "responder", "ambulance", "authority"],
            at=now,
        )
        db.add(event_exhausted)
        emergency.next_event_seq += 1

    # Professional ambulance track offer
    if orch_result.professional_plan and professional_track == TrackStatus.SEARCHING.value:
        top_ambulance = orch_result.professional_plan[0]
        amb_offer = DispatchOffer(
            emergency_id=emergency.id,
            track="professional",
            target_kind="ambulance",
            ambulance_id=top_ambulance.unit_id,
            rank=1,
            status=OfferStatus.OFFERED.value,
            offered_at=now,
            expires_at=now + timedelta(seconds=settings.OFFER_TTL_S),
            eta_s=top_ambulance.eta_s,
            distance_m=top_ambulance.distance_m,
            score_snapshot=top_ambulance.score_breakdown.model_dump(mode="json"),
        )
        db.add(amb_offer)
        emergency.professional_track = TrackStatus.OFFERED.value

        event_amb_offer = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="OFFER_CREATED",
            actor_user_id=None,
            actor_role="system",
            payload={
                "track": "professional",
                "ambulance_id": str(top_ambulance.unit_id),
                "rank": 1,
                "eta_s": top_ambulance.eta_s,
                "expires_at": amb_offer.expires_at.isoformat(),
            },
            visible_to=["citizen", "responder", "ambulance", "authority"],
            at=now,
        )
        db.add(event_amb_offer)
        emergency.next_event_seq += 1
    elif professional_track == TrackStatus.SEARCHING.value:
        emergency.professional_track = TrackStatus.UNAVAILABLE.value
        event_amb_exhausted = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="TRACK_EXHAUSTED",
            actor_user_id=None,
            actor_role="system",
            payload={"track": "professional", "reason": "No available ambulance units nearby"},
            visible_to=["citizen", "responder", "ambulance", "authority"],
            at=now,
        )
        db.add(event_amb_exhausted)
        emergency.next_event_seq += 1

    db.commit()
    db.refresh(emergency)
    return emergency, False
