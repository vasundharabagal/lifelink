"""Emergency incident API routes: creation, retrieval, advance, and lifecycle management (Spec §7.1, §10.3)."""
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.clock import Clock, get_clock
from app.core.db import get_db
from app.models.user import User
from app.schemas.emergency import (
    DuplicateEmergencyErrorResponse,
    EmergencyCreateRequest,
    EmergencyResponse,
)
from app.services.emergency import DuplicateEmergencyError, create_emergency

router = APIRouter(prefix="/emergencies", tags=["emergencies"])


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
