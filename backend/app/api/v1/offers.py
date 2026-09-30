"""Dispatch offers API routes: pending offers retrieval and responder action lifecycle (Spec §7.3, §10.3)."""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.clock import Clock, get_clock
from app.core.db import get_db
from app.domain.enums import OfferStatus, UserRole
from app.models.ambulance import AmbulanceUnit
from app.models.emergency import DispatchOffer, Emergency
from app.models.user import User
from app.schemas.offer import (
    DispatchOfferResponse,
    OfferActionRequest,
    PendingOffersResponse,
)
from app.services.offer import execute_offer_action
from app.services.privacy import filter_emergency_location_for_user

router = APIRouter(prefix="/offers", tags=["offers"])


def _project_offer_response(
    offer: DispatchOffer,
    emergency: Emergency,
    user: User,
) -> DispatchOfferResponse:
    """Project a DispatchOffer to DispatchOfferResponse applying location privacy tiers (CORE-07)."""
    lat, lng, tier, revoked = filter_emergency_location_for_user(
        emergency=emergency,
        user=user,
        active_offer=offer,
    )

    safety_warning = None
    if emergency.dispatch_plan and isinstance(emergency.dispatch_plan, dict):
        safety_warning = emergency.dispatch_plan.get("scene_safety_warning")

    return DispatchOfferResponse(
        id=offer.id,
        emergency_id=offer.emergency_id,
        track=offer.track,
        target_kind=offer.target_kind,
        responder_id=offer.responder_id,
        ambulance_id=offer.ambulance_id,
        rank=offer.rank,
        status=offer.status,
        offered_at=offer.offered_at,
        expires_at=offer.expires_at,
        responded_at=offer.responded_at,
        accepted_at=offer.accepted_at,
        arrived_at=offer.arrived_at,
        completed_at=offer.completed_at,
        decline_reason=offer.decline_reason,
        eta_s=offer.eta_s,
        distance_m=offer.distance_m,
        actions_reported=offer.actions_reported or [],
        notes=offer.notes,
        scene_safety_warning=safety_warning,
        lat=lat,
        lng=lng,
        location_tier=tier,
        location_revoked=revoked,
    )


@router.get(
    "/pending",
    response_model=PendingOffersResponse,
    summary="Retrieve active pending dispatch offers for the authenticated user (Spec §7.3)",
)
def get_pending_offers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    """Responder or operator queries pending offers currently waiting for their action."""
    now = clock.now(current_user.demo_session_id, db)
    offers = []

    if current_user.role == UserRole.RESPONDER.value:
        offers = (
            db.query(DispatchOffer)
            .filter(
                DispatchOffer.target_kind == "responder",
                DispatchOffer.responder_id == current_user.id,
                DispatchOffer.status == OfferStatus.OFFERED.value,
                DispatchOffer.expires_at > now,
            )
            .all()
        )
    elif current_user.role == UserRole.AMBULANCE_OPERATOR.value:
        offers = (
            db.query(DispatchOffer)
            .join(AmbulanceUnit, DispatchOffer.ambulance_id == AmbulanceUnit.id)
            .filter(
                DispatchOffer.target_kind == "ambulance",
                AmbulanceUnit.operator_user_id == current_user.id,
                DispatchOffer.status == OfferStatus.OFFERED.value,
                DispatchOffer.expires_at > now,
            )
            .all()
        )
    elif current_user.role == UserRole.AUTHORITY.value:
        offers = (
            db.query(DispatchOffer)
            .filter(
                DispatchOffer.status == OfferStatus.OFFERED.value,
                DispatchOffer.expires_at > now,
            )
            .all()
        )

    results = []
    for o in offers:
        em = db.query(Emergency).filter(Emergency.id == o.emergency_id).first()
        if em:
            results.append(_project_offer_response(o, em, current_user))

    return PendingOffersResponse(offers=results)


@router.post(
    "/{id}/action",
    response_model=DispatchOfferResponse,
    summary="Perform lifecycle action on a dispatch offer (ACCEPT, DECLINE, ARRIVE, SCENE_UNSAFE, COMPLETE)",
)
def act_on_offer(
    id: uuid.UUID,
    payload: OfferActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    """Execute lifecycle action on an offer with atomic race protection and cascading dispatch."""
    updated_offer = execute_offer_action(
        db=db,
        offer_id=id,
        action_req=payload,
        user=current_user,
        clock=clock,
    )
    emergency = db.query(Emergency).filter(Emergency.id == updated_offer.emergency_id).first()
    return _project_offer_response(updated_offer, emergency, current_user)
