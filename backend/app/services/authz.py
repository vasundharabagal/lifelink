"""Centralized object-level authorization service (AUTH-04, D-28, D-29, D-30).

Enforces:
1. Multi-tenant demo session isolation.
2. Incident ownership, participant, and authority access.
3. Anti-enumeration IDOR masking: unowned or cross-tenant resources return 404 NOT_FOUND.
4. Offer action permission checks (403 FORBIDDEN if caller is not the assigned responder/operator).
5. Medical profile consent gating (strictly hidden if consent_share_medical is False).
"""
from typing import Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import UserRole, OfferStatus, TargetKind
from app.models.user import User, MedicalProfile
from app.models.emergency import Emergency, DispatchOffer
from app.models.ambulance import AmbulanceUnit


def check_tenant_scope(user: User, resource_demo_session_id: Optional[uuid.UUID]) -> bool:
    """Verify that user and resource belong to the exact same demo session tenant (D-30)."""
    return user.demo_session_id == resource_demo_session_id


def assert_can_view_emergency(user: User, emergency: Emergency, db: Session) -> None:
    """Authorize access to emergency incident details (AUTH-04).
    
    Raises 404 NOT_FOUND on tenant mismatch or unauthorized access to prevent
    IDOR enumeration attacks (D-29).
    """
    # 1. Tenant boundary check
    if not check_tenant_scope(user, emergency.demo_session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Emergency not found"}},
        )

    # 2. Authority users have read access within their demo session
    if user.role == UserRole.AUTHORITY.value:
        return

    # 3. Patient or reporting citizen
    if user.id in (emergency.patient_user_id, emergency.reported_by_user_id):
        return

    # 4. Community responder with an active offer or assignment
    if user.role == UserRole.RESPONDER.value:
        offer = (
            db.query(DispatchOffer)
            .filter(
                DispatchOffer.emergency_id == emergency.id,
                DispatchOffer.responder_id == user.id,
            )
            .first()
        )
        if offer is not None:
            return

    # 5. Ambulance operator whose vehicle has an active offer or assignment
    if user.role == UserRole.AMBULANCE_OPERATOR.value:
        amb_offer = (
            db.query(DispatchOffer)
            .join(AmbulanceUnit, DispatchOffer.ambulance_id == AmbulanceUnit.id)
            .filter(
                DispatchOffer.emergency_id == emergency.id,
                AmbulanceUnit.operator_user_id == user.id,
            )
            .first()
        )
        if amb_offer is not None:
            return

    # 6. Anti-enumeration defense: return 404 rather than 403
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "NOT_FOUND", "message": "Emergency not found"}},
    )


def assert_can_act_on_offer(user: User, offer: DispatchOffer, db: Session) -> None:
    """Authorize action (accept, decline, update status) on a dispatch offer.
    
    Verifies tenant isolation and asserts that the caller is the assigned
    responder or ambulance unit operator.
    """
    # Tenant boundary check via parent emergency
    emergency = offer.emergency
    if emergency is None:
        emergency = db.query(Emergency).filter(Emergency.id == offer.emergency_id).first()

    if emergency is None or not check_tenant_scope(user, emergency.demo_session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Offer not found"}},
        )

    # Target kind validation
    if offer.target_kind == TargetKind.RESPONDER.value or offer.responder_id is not None:
        if offer.responder_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Offer not assigned to this responder"}},
            )
    elif offer.target_kind == TargetKind.AMBULANCE.value or offer.ambulance_id is not None:
        ambulance = offer.ambulance
        if ambulance is None and offer.ambulance_id is not None:
            ambulance = db.query(AmbulanceUnit).filter(AmbulanceUnit.id == offer.ambulance_id).first()

        if ambulance is None or ambulance.operator_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Offer not assigned to this ambulance operator"}},
            )


def assert_can_view_medical(
    user: User,
    emergency: Emergency,
    medical_profile: Optional[MedicalProfile],
    db: Session,
) -> bool:
    """Determine whether the caller is authorized to view patient medical profile (Spec §10.2).
    
    Medical profiles are strictly private and gated by explicit patient consent
    and accepted response assignment.
    """
    if medical_profile is None:
        return False

    if not check_tenant_scope(user, emergency.demo_session_id):
        return False

    # Patient always has access to their own medical profile
    if user.id == emergency.patient_user_id:
        return True

    # If patient has not explicitly consented to sharing medical data, deny for all others
    if not emergency.consent_share_medical:
        return False

    # Authorities have access during active emergency when consent is granted
    if user.role == UserRole.AUTHORITY.value:
        return True

    # Assigned responder with accepted offer
    if user.role == UserRole.RESPONDER.value:
        accepted = (
            db.query(DispatchOffer)
            .filter(
                DispatchOffer.emergency_id == emergency.id,
                DispatchOffer.responder_id == user.id,
                DispatchOffer.status == OfferStatus.ACCEPTED.value,
            )
            .first()
        )
        return accepted is not None

    # Assigned ambulance operator with accepted offer
    if user.role == UserRole.AMBULANCE_OPERATOR.value:
        accepted = (
            db.query(DispatchOffer)
            .join(AmbulanceUnit, DispatchOffer.ambulance_id == AmbulanceUnit.id)
            .filter(
                DispatchOffer.emergency_id == emergency.id,
                AmbulanceUnit.operator_user_id == user.id,
                DispatchOffer.status == OfferStatus.ACCEPTED.value,
            )
            .first()
        )
        return accepted is not None

    return False
