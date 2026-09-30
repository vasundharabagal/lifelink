"""Emergency incident API routes: creation, retrieval, advance, and lifecycle management (Spec §7.1, §10.3)."""
from datetime import timedelta
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.clock import Clock, get_clock
from app.core.db import get_db
from app.models.emergency import Emergency, EmergencyEvent
from app.models.user import User
from app.schemas.emergency import (
    DuplicateEmergencyErrorResponse,
    EmergencyAdvanceRequest,
    EmergencyCreateRequest,
    EmergencyEventResponse,
    EmergencyResponse,
)
from app.services.advance import advance_emergency
from app.services.authz import assert_can_view_emergency
from app.services.emergency import DuplicateEmergencyError, create_emergency

router = APIRouter(prefix="/emergencies", tags=["emergencies"])


class OffsetClock(Clock):
    """Temporary virtual clock wrapper applying a transient offset in seconds without modifying persistent state."""
    def __init__(self, base_clock: Clock, offset_seconds: int):
        self.base_clock = base_clock
        self.offset = timedelta(seconds=offset_seconds)

    def now(self, demo_session_id: Optional[uuid.UUID] = None, db: Optional[Session] = None):
        return self.base_clock.now(demo_session_id, db) + self.offset


@router.post(
    "",
    response_model=EmergencyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new emergency incident with dual-track dispatch (Spec §7.1)",
)
def submit_emergency(
    payload: EmergencyCreateRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    """Citizen creates an emergency incident with idempotency replay and 150m deduplication."""
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    try:
        emergency, is_replayed = create_emergency(
            db=db,
            payload=payload,
            reporter_user=current_user,
            clock=clock,
            idempotency_key=idempotency_key,
        )
    except DuplicateEmergencyError as e:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=e.detail.model_dump(mode="json"),
        )

    if is_replayed:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED

    return emergency


@router.get(
    "/{id}",
    response_model=EmergencyResponse,
    summary="Retrieve incident state with transparent lazy evaluation (CORE-03, Spec §7.2)",
)
def get_emergency(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    """Client polling endpoint that lazily advances timeouts, cascades offers, and returns fresh incident state."""
    # 1. Lazily advance state machine under row lock
    emergency = advance_emergency(db=db, emergency_id=id, clock=clock)

    # 2. Authorization check against current caller
    assert_can_view_emergency(user=current_user, emergency=emergency, db=db)

    return emergency


@router.post(
    "/{id}/advance",
    response_model=EmergencyResponse,
    summary="Explicitly advance incident state machine with optional clock offset (CORE-03, D-05)",
)
def advance_emergency_endpoint(
    id: uuid.UUID,
    payload: Optional[EmergencyAdvanceRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    """Explicitly advance emergency timeouts and cascades for testing and Demo Director."""
    effective_clock = clock
    if payload and payload.offset_seconds > 0:
        effective_clock = OffsetClock(clock, payload.offset_seconds)

    emergency = advance_emergency(db=db, emergency_id=id, clock=effective_clock)
    assert_can_view_emergency(user=current_user, emergency=emergency, db=db)
    return emergency


@router.get(
    "/{id}/timeline",
    response_model=List[EmergencyEventResponse],
    summary="Retrieve append-only audit timeline events filtered by role visibility (Spec §12.3)",
)
def get_emergency_timeline(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve chronological event stream filtered by caller visibility."""
    emergency = db.query(Emergency).filter(Emergency.id == id).first()
    if not emergency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Emergency not found"}},
        )

    assert_can_view_emergency(user=current_user, emergency=emergency, db=db)

    events = (
        db.query(EmergencyEvent)
        .filter(EmergencyEvent.emergency_id == id)
        .order_by(EmergencyEvent.seq.asc())
        .all()
    )

    filtered_events = [
        e for e in events
        if not e.visible_to or current_user.role in e.visible_to or current_user.role == "authority"
    ]
    return filtered_events
