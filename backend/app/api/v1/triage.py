"""Triage evaluation and preview endpoints (Spec §8.2)."""
import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.core.clock import get_clock
from app.domain.enums import UserRole
from app.models.user import User
from app.schemas.triage import TriageInput, TriageResult
from app.services.audit import log_audit_event
from app.services.rate_limiter import check_triage_preview_rate_limit
from app.triage.service import triage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post(
    "/preview",
    response_model=TriageResult,
    summary="Evaluate citizen triage inputs without persisting emergency",
)
async def preview_triage(
    input_data: TriageInput,
    request: Request,
    current_user: User = Depends(require_role(UserRole.CITIZEN)),
    db: Session = Depends(get_db),
) -> TriageResult:
    """Evaluate quick-type, answers, and free-text description for triage severity preview.
    
    Persists nothing to emergencies table. Enforces DB-derived rate limit
    (maximum 20 per 10 minutes) and logs an audit entry.
    """
    clock = get_clock()

    # Rate limiting check
    check_triage_preview_rate_limit(
        user_id=current_user.id,
        db=db,
        clock=clock,
        demo_session_id=current_user.demo_session_id,
    )

    # Evaluate triage
    is_demo = current_user.demo_session_id is not None
    result = await triage_service.evaluate_triage(
        input_data=input_data,
        is_demo=is_demo,
        db=db,
        user_id=current_user.id,
    )

    # Log audit event for preview activity
    client_ip = request.client.host if request.client else "unknown"
    log_audit_event(
        db=db,
        action="triage_preview",
        resource_type="triage",
        resource_id="preview",
        outcome="allow",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        client_ip=client_ip,
        meta={
            "priority": result.priority.value,
            "protocol_id": result.protocol_id.value,
            "source": result.source,
        },
    )

    return result
