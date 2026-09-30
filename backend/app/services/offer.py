"""Transactional offer action lifecycle service (Spec §7.3, CORE-04, CORE-05).

Enforces:
1. Atomic single-active-responder constraint (409 OFFER_ALREADY_CLAIMED).
2. Lifecycle state machine: OFFERED -> ACCEPTED -> ARRIVED -> COMPLETED.
3. Synchronous cascading dispatch on DECLINE or SCENE_UNSAFE to candidate #2.
4. Scene hazard logging and dispatch plan tagging on SCENE_UNSAFE.
5. Append-only chronological timeline event generation.
"""
from datetime import timedelta
from typing import Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import settings
from app.domain.enums import (
    EmergencyStatus,
    OfferAction,
    OfferStatus,
    TrackStatus,
    UserRole,
)
from app.models.ambulance import AmbulanceUnit
from app.models.emergency import DispatchOffer, Emergency, EmergencyEvent
from app.models.user import User
from app.orchestration.service import find_and_rank_candidates
from app.schemas.offer import OfferActionRequest
from app.services.authz import check_tenant_scope


def execute_offer_action(
    db: Session,
    offer_id: uuid.UUID,
    action_req: OfferActionRequest,
    user: User,
    clock: Clock,
) -> DispatchOffer:
    """Execute responder or operator action on a dispatch offer under PostgreSQL row locks."""
    # 1. Acquire row lock on DispatchOffer
    offer = (
        db.query(DispatchOffer)
        .filter(DispatchOffer.id == offer_id)
        .with_for_update()
        .one_or_none()
    )
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Offer not found"}},
        )

    # 2. Acquire row lock on parent Emergency
    emergency = (
        db.query(Emergency)
        .filter(Emergency.id == offer.emergency_id)
        .with_for_update()
        .one_or_none()
    )
    if not emergency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Emergency not found"}},
        )

    # 3. Multi-tenant scope check
    if not check_tenant_scope(user, emergency.demo_session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Offer not found"}},
        )

    # 4. Caller authorization check
    is_authorized = False
    if user.role == UserRole.AUTHORITY.value:
        is_authorized = True
    elif offer.target_kind == "responder" and offer.responder_id == user.id:
        is_authorized = True
    elif offer.target_kind == "ambulance" and offer.ambulance_id:
        amb = db.query(AmbulanceUnit).filter(AmbulanceUnit.id == offer.ambulance_id).first()
        if amb and amb.operator_user_id == user.id:
            is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "You are not authorized to act on this offer"}},
        )

    now = clock.now(emergency.demo_session_id, db)

    # 5. Handle action dispatch
    if action_req.action == OfferAction.ACCEPT:
        if offer.status in (OfferStatus.ACCEPTED.value, OfferStatus.ARRIVED.value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "OFFER_ALREADY_CLAIMED", "message": "This offer has already been accepted"}},
            )

        if offer.status != OfferStatus.OFFERED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "INVALID_STATE", "message": f"Cannot accept offer in state '{offer.status}'"}},
            )

        if now >= offer.expires_at:
            offer.status = OfferStatus.EXPIRED.value
            offer.responded_at = now
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={"error": {"code": "OFFER_EXPIRED", "message": "This offer has expired"}},
            )

        # Single active responder constraint (CORE-04, T-05-02)
        already_claimed = (
            db.query(DispatchOffer)
            .filter(
                DispatchOffer.emergency_id == emergency.id,
                DispatchOffer.track == offer.track,
                DispatchOffer.id != offer.id,
                DispatchOffer.status.in_([OfferStatus.ACCEPTED.value, OfferStatus.ARRIVED.value]),
            )
            .first()
        )
        if already_claimed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "OFFER_ALREADY_CLAIMED", "message": "Another responder has already claimed this incident"}},
            )

        offer.status = OfferStatus.ACCEPTED.value
        offer.accepted_at = now
        offer.responded_at = now

        if offer.track == "community":
            emergency.community_track = TrackStatus.ASSIGNED.value
        elif offer.track == "professional":
            emergency.professional_track = TrackStatus.ASSIGNED.value

        if emergency.status in (
            EmergencyStatus.CREATED.value,
            EmergencyStatus.TRIAGED.value,
            EmergencyStatus.DISPATCHING.value,
        ):
            emergency.status = EmergencyStatus.IN_PROGRESS.value

        event_accept = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="OFFER_ACCEPTED",
            actor_user_id=user.id,
            actor_role=user.role,
            payload={
                "track": offer.track,
                "offer_id": str(offer.id),
                "rank": offer.rank,
                "responder_name": user.full_name,
            },
            visible_to=["citizen", "responder", "ambulance_operator", "authority"],
            at=now,
        )
        emergency.next_event_seq += 1
        db.add(event_accept)

    elif action_req.action == OfferAction.DECLINE:
        if offer.status != OfferStatus.OFFERED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "INVALID_STATE", "message": f"Cannot decline offer in state '{offer.status}'"}},
            )

        offer.status = OfferStatus.DECLINED.value
        offer.decline_reason = action_req.decline_reason or "UNAVAILABLE"
        offer.responded_at = now
        offer.notes = action_req.notes

        event_decline = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="OFFER_DECLINED",
            actor_user_id=user.id,
            actor_role=user.role,
            payload={
                "track": offer.track,
                "offer_id": str(offer.id),
                "reason": offer.decline_reason,
                "rank": offer.rank,
            },
            visible_to=["citizen", "responder", "ambulance_operator", "authority"],
            at=now,
        )
        emergency.next_event_seq += 1
        db.add(event_decline)
        db.flush()

        # Immediate synchronous cascade to candidate #2 (CORE-05, D-06)
        _cascade_next_candidate(db, emergency, offer, now, clock)

    elif action_req.action == OfferAction.ARRIVE:
        if offer.status != OfferStatus.ACCEPTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "INVALID_STATE", "message": f"Must be in ACCEPTED state to report arrival (current: '{offer.status}')"}},
            )

        offer.status = OfferStatus.ARRIVED.value
        offer.arrived_at = now

        if offer.track == "community":
            emergency.community_track = TrackStatus.ON_SCENE.value
        elif offer.track == "professional":
            emergency.professional_track = TrackStatus.ON_SCENE.value

        event_arrive = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="RESPONDER_ARRIVED",
            actor_user_id=user.id,
            actor_role=user.role,
            payload={
                "track": offer.track,
                "offer_id": str(offer.id),
                "responder_name": user.full_name,
            },
            visible_to=["citizen", "responder", "ambulance_operator", "authority"],
            at=now,
        )
        emergency.next_event_seq += 1
        db.add(event_arrive)

    elif action_req.action == OfferAction.SCENE_UNSAFE:
        if offer.status not in (OfferStatus.ACCEPTED.value, OfferStatus.ARRIVED.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "INVALID_STATE", "message": f"Cannot report scene unsafe from state '{offer.status}'"}},
            )

        offer.status = OfferStatus.CANCELLED.value
        hazard_note = action_req.notes or "Responder reported scene unsafe"
        offer.notes = hazard_note
        offer.decline_reason = "SCENE_UNSAFE"

        # Tag incident dispatch plan with hazard warning
        plan = dict(emergency.dispatch_plan or {})
        plan["scene_safety_warning"] = hazard_note
        emergency.dispatch_plan = plan

        event_hazard = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="RESPONDER_SCENE_UNSAFE",
            actor_user_id=user.id,
            actor_role=user.role,
            payload={
                "track": offer.track,
                "offer_id": str(offer.id),
                "warning": hazard_note,
            },
            visible_to=["citizen", "responder", "ambulance_operator", "authority"],
            at=now,
        )
        emergency.next_event_seq += 1
        db.add(event_hazard)
        db.flush()

        # Immediate synchronous cascade to candidate #2 with safety warning (D-07)
        _cascade_next_candidate(db, emergency, offer, now, clock, hazard_note=hazard_note)

    elif action_req.action == OfferAction.COMPLETE:
        if offer.status != OfferStatus.ARRIVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "INVALID_STATE", "message": f"Must be in ARRIVED state to complete assignment (current: '{offer.status}')"}},
            )

        offer.status = OfferStatus.COMPLETED.value
        offer.completed_at = now
        offer.actions_reported = action_req.actions_reported
        offer.notes = action_req.notes

        if offer.track == "community":
            emergency.community_track = TrackStatus.DONE.value
        elif offer.track == "professional":
            emergency.professional_track = TrackStatus.DONE.value

        event_complete = EmergencyEvent(
            emergency_id=emergency.id,
            seq=emergency.next_event_seq,
            type="RESPONDER_COMPLETED",
            actor_user_id=user.id,
            actor_role=user.role,
            payload={
                "track": offer.track,
                "offer_id": str(offer.id),
                "actions_reported": action_req.actions_reported,
                "notes": action_req.notes,
            },
            visible_to=["citizen", "responder", "ambulance_operator", "authority"],
            at=now,
        )
        emergency.next_event_seq += 1
        db.add(event_complete)

    # 6. Synchronize emergency metadata
    emergency.updated_at = now
    emergency.version += 1

    db.commit()
    db.refresh(offer)
    return offer


def _cascade_next_candidate(
    db: Session,
    emergency: Emergency,
    declined_offer: DispatchOffer,
    now,
    clock: Clock,
    hazard_note: Optional[str] = None,
) -> None:
    """Find and dispatch the next ranked candidate on track following decline, timeout, or safety cancellation."""
    orch_res = find_and_rank_candidates(db, emergency.id, clock)

    if declined_offer.track == "community":
        if orch_res.community_plan:
            next_cand = orch_res.community_plan[0]
            ttl_s = settings.OFFER_TTL_S
            new_comm_offer = DispatchOffer(
                emergency_id=emergency.id,
                track="community",
                target_kind="responder",
                responder_id=next_cand.candidate_id,
                rank=declined_offer.rank + 1,
                status=OfferStatus.OFFERED.value,
                offered_at=now,
                expires_at=now + timedelta(seconds=ttl_s),
                eta_s=next_cand.eta_s,
                distance_m=next_cand.distance_m,
                score_snapshot=next_cand.score_breakdown.model_dump(mode="json"),
                notes=hazard_note,
            )
            db.add(new_comm_offer)
            db.flush()

            payload = {
                "track": "community",
                "offer_id": str(new_comm_offer.id),
                "responder_id": str(next_cand.candidate_id),
                "responder_name": next_cand.full_name,
                "category": next_cand.category.value,
                "rank": new_comm_offer.rank,
                "eta_s": next_cand.eta_s,
                "distance_m": next_cand.distance_m,
            }
            if hazard_note:
                payload["scene_safety_warning"] = hazard_note

            event_created = EmergencyEvent(
                emergency_id=emergency.id,
                seq=emergency.next_event_seq,
                type="OFFER_CREATED",
                actor_role="system",
                payload=payload,
                visible_to=["citizen", "responder", "ambulance_operator", "authority"],
                at=now,
            )
            emergency.next_event_seq += 1
            db.add(event_created)
            emergency.community_track = TrackStatus.OFFERED.value
        else:
            emergency.community_track = TrackStatus.UNAVAILABLE.value
            event_exhausted = EmergencyEvent(
                emergency_id=emergency.id,
                seq=emergency.next_event_seq,
                type="TRACK_EXHAUSTED",
                actor_role="system",
                payload={"track": "community", "reason": "NO_ELIGIBLE_RESPONDERS"},
                visible_to=["citizen", "authority"],
                at=now,
            )
            emergency.next_event_seq += 1
            db.add(event_exhausted)

    elif declined_offer.track == "professional":
        if orch_res.professional_plan:
            next_amb = orch_res.professional_plan[0]
            ttl_s = settings.OFFER_TTL_S
            new_amb_offer = DispatchOffer(
                emergency_id=emergency.id,
                track="professional",
                target_kind="ambulance",
                ambulance_id=next_amb.unit_id,
                rank=declined_offer.rank + 1,
                status=OfferStatus.OFFERED.value,
                offered_at=now,
                expires_at=now + timedelta(seconds=ttl_s),
                eta_s=next_amb.eta_s,
                distance_m=next_amb.distance_m,
                score_snapshot=next_amb.score_breakdown.model_dump(mode="json"),
                notes=hazard_note,
            )
            db.add(new_amb_offer)
            db.flush()

            payload = {
                "track": "professional",
                "offer_id": str(new_amb_offer.id),
                "ambulance_id": str(next_amb.unit_id),
                "callsign": next_amb.callsign,
                "unit_type": next_amb.unit_type.value,
                "rank": new_amb_offer.rank,
                "eta_s": next_amb.eta_s,
                "distance_m": next_amb.distance_m,
            }
            if hazard_note:
                payload["scene_safety_warning"] = hazard_note

            event_created = EmergencyEvent(
                emergency_id=emergency.id,
                seq=emergency.next_event_seq,
                type="OFFER_CREATED",
                actor_role="system",
                payload=payload,
                visible_to=["citizen", "responder", "ambulance_operator", "authority"],
                at=now,
            )
            emergency.next_event_seq += 1
            db.add(event_created)
            emergency.professional_track = TrackStatus.OFFERED.value
        else:
            emergency.professional_track = TrackStatus.UNAVAILABLE.value
            event_exhausted = EmergencyEvent(
                emergency_id=emergency.id,
                seq=emergency.next_event_seq,
                type="TRACK_EXHAUSTED",
                actor_role="system",
                payload={"track": "professional", "reason": "NO_ELIGIBLE_AMBULANCES"},
                visible_to=["citizen", "authority"],
                at=now,
            )
            emergency.next_event_seq += 1
            db.add(event_exhausted)
