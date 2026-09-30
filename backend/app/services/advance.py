"""Deterministic lazy evaluation engine for emergency state machine (Spec §7.2, CORE-03, CORE-05).

Executes under PostgreSQL row-level locks (SELECT FOR UPDATE) to advance incident states,
expire unacknowledged offers, cascade to candidate #2, and close unserved incidents
deterministically during client HTTP polling without persistent background cron workers.
"""
from datetime import timedelta
from typing import Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import settings
from app.domain.enums import EmergencyStatus, OfferStatus, TrackStatus, UserRole
from app.models.emergency import DispatchOffer, Emergency, EmergencyEvent
from app.orchestration.service import find_and_rank_candidates


def advance_emergency(
    db: Session,
    emergency_id: uuid.UUID,
    clock: Clock,
) -> Emergency:
    """Lazily advance state machine under PostgreSQL row lock (SELECT FOR UPDATE).
    
    1. Locks Emergency row to prevent concurrent race conditions (T-05-08).
    2. Checks offer timeout expiry (OFFER_TTL_S) against clock.now().
    3. Expires unacknowledged offers and immediately cascades to candidate #2 (CORE-05).
    4. Detects track exhaustion and sets UNAVAILABLE when candidates run out.
    5. Closes incidents with NO_COVERAGE_CLOSED if all tracks are exhausted.
    6. Appends audit timeline events with serialized sequence numbers (T-05-09).
    """
    # 1. Acquire row lock on parent Emergency entity first (Lock hierarchy root)
    emergency = (
        db.query(Emergency)
        .filter(Emergency.id == emergency_id)
        .with_for_update()
        .one_or_none()
    )
    if emergency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Emergency not found"}},
        )

    # 2. Terminal state check: completed/cancelled incidents are immutable
    if emergency.status in (
        EmergencyStatus.COMPLETED.value,
        EmergencyStatus.CANCELLED.value,
        EmergencyStatus.NO_COVERAGE_CLOSED.value,
    ):
        return emergency

    now = clock.now(emergency.demo_session_id, db)
    changed = False

    # 3. Evaluate Community Track
    if emergency.community_track in (TrackStatus.SEARCHING.value, TrackStatus.OFFERED.value):
        active_comm_offer = (
            db.query(DispatchOffer)
            .filter(
                DispatchOffer.emergency_id == emergency.id,
                DispatchOffer.track == "community",
                DispatchOffer.status.in_([
                    OfferStatus.OFFERED.value,
                    OfferStatus.ACCEPTED.value,
                    OfferStatus.ARRIVED.value,
                ]),
            )
            .with_for_update()
            .order_by(DispatchOffer.rank.desc())
            .first()
        )

        if active_comm_offer and active_comm_offer.status == OfferStatus.OFFERED.value:
            # Check if offer has timed out
            if now >= active_comm_offer.expires_at:
                active_comm_offer.status = OfferStatus.EXPIRED.value
                active_comm_offer.responded_at = now
                changed = True

                event_expired = EmergencyEvent(
                    emergency_id=emergency.id,
                    seq=emergency.next_event_seq,
                    type="OFFER_EXPIRED",
                    actor_user_id=active_comm_offer.responder_id,
                    actor_role="system",
                    payload={
                        "track": "community",
                        "offer_id": str(active_comm_offer.id),
                        "responder_id": str(active_comm_offer.responder_id) if active_comm_offer.responder_id else None,
                        "rank": active_comm_offer.rank,
                        "reason": "OFFER_TTL_EXPIRED",
                    },
                    visible_to=["citizen", "responder", "ambulance_operator", "authority"],
                    at=now,
                )
                emergency.next_event_seq += 1
                db.add(event_expired)
                db.flush()

                # Cascading dispatch: query remaining candidates
                orch_res = find_and_rank_candidates(db, emergency.id, clock)
                if orch_res.community_plan:
                    next_cand = orch_res.community_plan[0]
                    ttl_s = settings.OFFER_TTL_S
                    new_comm_offer = DispatchOffer(
                        emergency_id=emergency.id,
                        track="community",
                        target_kind="responder",
                        responder_id=next_cand.candidate_id,
                        rank=active_comm_offer.rank + 1,
                        status=OfferStatus.OFFERED.value,
                        offered_at=now,
                        expires_at=now + timedelta(seconds=ttl_s),
                        eta_s=next_cand.eta_s,
                        distance_m=next_cand.distance_m,
                        score_snapshot=next_cand.score_breakdown.model_dump(mode="json"),
                    )
                    db.add(new_comm_offer)
                    db.flush()

                    event_created = EmergencyEvent(
                        emergency_id=emergency.id,
                        seq=emergency.next_event_seq,
                        type="OFFER_CREATED",
                        actor_role="system",
                        payload={
                            "track": "community",
                            "offer_id": str(new_comm_offer.id),
                            "responder_id": str(next_cand.candidate_id),
                            "responder_name": next_cand.full_name,
                            "category": next_cand.category.value,
                            "rank": new_comm_offer.rank,
                            "eta_s": next_cand.eta_s,
                            "distance_m": next_cand.distance_m,
                        },
                        visible_to=["citizen", "responder", "ambulance_operator", "authority"],
                        at=now,
                    )
                    emergency.next_event_seq += 1
                    db.add(event_created)
                    emergency.community_track = TrackStatus.OFFERED.value
                else:
                    # Candidates exhausted
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
                changed = True

        elif not active_comm_offer and emergency.community_track == TrackStatus.SEARCHING.value:
            # No active offer yet on searching community track
            orch_res = find_and_rank_candidates(db, emergency.id, clock)
            if orch_res.community_plan:
                cand = orch_res.community_plan[0]
                ttl_s = settings.OFFER_TTL_S
                new_comm_offer = DispatchOffer(
                    emergency_id=emergency.id,
                    track="community",
                    target_kind="responder",
                    responder_id=cand.candidate_id,
                    rank=1,
                    status=OfferStatus.OFFERED.value,
                    offered_at=now,
                    expires_at=now + timedelta(seconds=ttl_s),
                    eta_s=cand.eta_s,
                    distance_m=cand.distance_m,
                    score_snapshot=cand.score_breakdown.model_dump(mode="json"),
                )
                db.add(new_comm_offer)
                db.flush()

                event_created = EmergencyEvent(
                    emergency_id=emergency.id,
                    seq=emergency.next_event_seq,
                    type="OFFER_CREATED",
                    actor_role="system",
                    payload={
                        "track": "community",
                        "offer_id": str(new_comm_offer.id),
                        "responder_id": str(cand.candidate_id),
                        "responder_name": cand.full_name,
                        "category": cand.category.value,
                        "rank": 1,
                        "eta_s": cand.eta_s,
                        "distance_m": cand.distance_m,
                    },
                    visible_to=["citizen", "responder", "ambulance_operator", "authority"],
                    at=now,
                )
                emergency.next_event_seq += 1
                db.add(event_created)
                emergency.community_track = TrackStatus.OFFERED.value
                changed = True
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
                changed = True

    # 4. Evaluate Professional Ambulance Track
    if emergency.professional_track in (TrackStatus.SEARCHING.value, TrackStatus.OFFERED.value):
        active_amb_offer = (
            db.query(DispatchOffer)
            .filter(
                DispatchOffer.emergency_id == emergency.id,
                DispatchOffer.track == "professional",
                DispatchOffer.status.in_([
                    OfferStatus.OFFERED.value,
                    OfferStatus.ACCEPTED.value,
                    OfferStatus.ARRIVED.value,
                ]),
            )
            .with_for_update()
            .order_by(DispatchOffer.rank.desc())
            .first()
        )

        if active_amb_offer and active_amb_offer.status == OfferStatus.OFFERED.value:
            if now >= active_amb_offer.expires_at:
                active_amb_offer.status = OfferStatus.EXPIRED.value
                active_amb_offer.responded_at = now
                changed = True

                event_expired = EmergencyEvent(
                    emergency_id=emergency.id,
                    seq=emergency.next_event_seq,
                    type="OFFER_EXPIRED",
                    actor_role="system",
                    payload={
                        "track": "professional",
                        "offer_id": str(active_amb_offer.id),
                        "ambulance_id": str(active_amb_offer.ambulance_id) if active_amb_offer.ambulance_id else None,
                        "rank": active_amb_offer.rank,
                        "reason": "OFFER_TTL_EXPIRED",
                    },
                    visible_to=["citizen", "responder", "ambulance_operator", "authority"],
                    at=now,
                )
                emergency.next_event_seq += 1
                db.add(event_expired)
                db.flush()

                orch_res = find_and_rank_candidates(db, emergency.id, clock)
                if orch_res.professional_plan:
                    next_amb = orch_res.professional_plan[0]
                    ttl_s = settings.OFFER_TTL_S
                    new_amb_offer = DispatchOffer(
                        emergency_id=emergency.id,
                        track="professional",
                        target_kind="ambulance",
                        ambulance_id=next_amb.unit_id,
                        rank=active_amb_offer.rank + 1,
                        status=OfferStatus.OFFERED.value,
                        offered_at=now,
                        expires_at=now + timedelta(seconds=ttl_s),
                        eta_s=next_amb.eta_s,
                        distance_m=next_amb.distance_m,
                        score_snapshot=next_amb.score_breakdown.model_dump(mode="json"),
                    )
                    db.add(new_amb_offer)
                    db.flush()

                    event_created = EmergencyEvent(
                        emergency_id=emergency.id,
                        seq=emergency.next_event_seq,
                        type="OFFER_CREATED",
                        actor_role="system",
                        payload={
                            "track": "professional",
                            "offer_id": str(new_amb_offer.id),
                            "ambulance_id": str(next_amb.unit_id),
                            "callsign": next_amb.callsign,
                            "unit_type": next_amb.unit_type.value,
                            "rank": new_amb_offer.rank,
                            "eta_s": next_amb.eta_s,
                            "distance_m": next_amb.distance_m,
                        },
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
                changed = True

        elif not active_amb_offer and emergency.professional_track == TrackStatus.SEARCHING.value:
            orch_res = find_and_rank_candidates(db, emergency.id, clock)
            if orch_res.professional_plan:
                amb = orch_res.professional_plan[0]
                ttl_s = settings.OFFER_TTL_S
                new_amb_offer = DispatchOffer(
                    emergency_id=emergency.id,
                    track="professional",
                    target_kind="ambulance",
                    ambulance_id=amb.unit_id,
                    rank=1,
                    status=OfferStatus.OFFERED.value,
                    offered_at=now,
                    expires_at=now + timedelta(seconds=ttl_s),
                    eta_s=amb.eta_s,
                    distance_m=amb.distance_m,
                    score_snapshot=amb.score_breakdown.model_dump(mode="json"),
                )
                db.add(new_amb_offer)
                db.flush()

                event_created = EmergencyEvent(
                    emergency_id=emergency.id,
                    seq=emergency.next_event_seq,
                    type="OFFER_CREATED",
                    actor_role="system",
                    payload={
                        "track": "professional",
                        "offer_id": str(new_amb_offer.id),
                        "ambulance_id": str(amb.unit_id),
                        "callsign": amb.callsign,
                        "unit_type": amb.unit_type.value,
                        "rank": 1,
                        "eta_s": amb.eta_s,
                        "distance_m": amb.distance_m,
                    },
                    visible_to=["citizen", "responder", "ambulance_operator", "authority"],
                    at=now,
                )
                emergency.next_event_seq += 1
                db.add(event_created)
                emergency.professional_track = TrackStatus.OFFERED.value
                changed = True
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
                changed = True

    # 5. Check No Coverage Condition
    if emergency.community_track in (TrackStatus.UNAVAILABLE.value, TrackStatus.NOT_STARTED.value) and \
       emergency.professional_track in (TrackStatus.UNAVAILABLE.value, TrackStatus.NOT_STARTED.value):
        has_active_assignment = (
            db.query(DispatchOffer)
            .filter(
                DispatchOffer.emergency_id == emergency.id,
                DispatchOffer.status.in_([OfferStatus.ACCEPTED.value, OfferStatus.ARRIVED.value]),
            )
            .first()
            is not None
        )
        if not has_active_assignment:
            emergency.status = EmergencyStatus.NO_COVERAGE_CLOSED.value
            emergency.close_reason = "NO_COVERAGE"
            emergency.closed_at = now
            changed = True

            event_closed = EmergencyEvent(
                emergency_id=emergency.id,
                seq=emergency.next_event_seq,
                type="EMERGENCY_CLOSED",
                actor_role="system",
                payload={"reason": "NO_COVERAGE"},
                visible_to=["citizen", "authority"],
                at=now,
            )
            emergency.next_event_seq += 1
            db.add(event_closed)

    # 6. Synchronize changes
    if changed:
        emergency.updated_at = now
        emergency.version += 1

    db.commit()
    db.refresh(emergency)
    return emergency
