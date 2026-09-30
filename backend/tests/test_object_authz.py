"""Object-level authorization and anti-enumeration test suite (AUTH-04).

Verifies:
1. IDOR anti-enumeration defense: Unowned/unrelated emergencies return 404 NOT_FOUND.
2. Multi-tenant isolation: Cross-demo-session access returns 404 NOT_FOUND.
3. Incident participation access: Patient, reporter, assigned responder, and authority permitted.
4. Offer action protection: 403 FORBIDDEN when acting on another responder's offer.
5. Medical profile consent gating: Strict consent requirement and offer acceptance verification.
"""
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi import HTTPException

from app.domain.enums import UserRole, OfferStatus, TargetKind, Priority, EmergencyType, EmergencyStatus, TrackStatus
from app.models.user import User, MedicalProfile
from app.models.emergency import Emergency, DispatchOffer
from app.models.ambulance import AmbulanceUnit
from app.services.authz import (
    assert_can_view_emergency,
    assert_can_act_on_offer,
    assert_can_view_medical,
    check_tenant_scope,
)


@pytest.fixture
def test_users(db_session):
    """Fixture providing isolated users across roles and demo sessions."""
    session_1 = uuid.uuid4()
    session_2 = uuid.uuid4()

    citizen_a = User(
        email=f"cit_a_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Citizen A (Reporter/Patient)",
        role=UserRole.CITIZEN.value,
        demo_session_id=session_1,
        is_active=True,
    )
    citizen_b = User(
        email=f"cit_b_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Citizen B (Unrelated)",
        role=UserRole.CITIZEN.value,
        demo_session_id=session_1,
        is_active=True,
    )
    responder_a = User(
        email=f"resp_a_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Responder A",
        role=UserRole.RESPONDER.value,
        demo_session_id=session_1,
        is_active=True,
    )
    responder_b = User(
        email=f"resp_b_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Responder B",
        role=UserRole.RESPONDER.value,
        demo_session_id=session_1,
        is_active=True,
    )
    operator_a = User(
        email=f"op_a_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Operator A",
        role=UserRole.AMBULANCE_OPERATOR.value,
        demo_session_id=session_1,
        is_active=True,
    )
    operator_b = User(
        email=f"op_b_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Operator B",
        role=UserRole.AMBULANCE_OPERATOR.value,
        demo_session_id=session_1,
        is_active=True,
    )
    authority_user = User(
        email=f"auth_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Authority Admin",
        role=UserRole.AUTHORITY.value,
        demo_session_id=session_1,
        is_active=True,
    )
    cross_tenant_user = User(
        email=f"cross_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Cross-Tenant Citizen",
        role=UserRole.CITIZEN.value,
        demo_session_id=session_2,
        is_active=True,
    )

    db_session.add_all([
        citizen_a,
        citizen_b,
        responder_a,
        responder_b,
        operator_a,
        operator_b,
        authority_user,
        cross_tenant_user,
    ])
    db_session.flush()

    return {
        "session_1": session_1,
        "session_2": session_2,
        "citizen_a": citizen_a,
        "citizen_b": citizen_b,
        "responder_a": responder_a,
        "responder_b": responder_b,
        "operator_a": operator_a,
        "operator_b": operator_b,
        "authority": authority_user,
        "cross_tenant": cross_tenant_user,
    }


@pytest.fixture
def sample_emergency(db_session, test_users):
    """Fixture providing a standard emergency incident."""
    emergency = Emergency(
        patient_user_id=test_users["citizen_a"].id,
        reported_by_user_id=test_users["citizen_a"].id,
        idempotency_key=f"idem_{uuid.uuid4().hex}",
        status=EmergencyStatus.DISPATCHING.value,
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.CHEST_PAIN.value,
        triage={"chief_complaint": "Severe chest pressure"},
        dispatch_plan={},
        lat=18.5204,
        lng=73.8567,
        consent_share_medical=False,
        demo_session_id=test_users["session_1"],
    )
    db_session.add(emergency)
    db_session.flush()
    return emergency


def test_emergency_ownership_idor_masking(db_session, test_users, sample_emergency):
    """Verify unrelated citizen receives 404 NOT_FOUND rather than 403 (AUTH-04, D-29)."""
    with pytest.raises(HTTPException) as exc_info:
        assert_can_view_emergency(test_users["citizen_b"], sample_emergency, db_session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "NOT_FOUND"


def test_tenant_isolation(db_session, test_users, sample_emergency):
    """Verify cross-tenant user receives 404 NOT_FOUND even if patient ID matched (AUTH-04, D-30)."""
    # Attempt access with a user in session_2
    with pytest.raises(HTTPException) as exc_info:
        assert_can_view_emergency(test_users["cross_tenant"], sample_emergency, db_session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "NOT_FOUND"


def test_participant_access(db_session, test_users, sample_emergency):
    """Verify patient, reporter, assigned responder, and authority can view emergency."""
    # 1. Patient
    assert_can_view_emergency(test_users["citizen_a"], sample_emergency, db_session)

    # 2. Authority
    assert_can_view_emergency(test_users["authority"], sample_emergency, db_session)

    # 3. Responder before offer: raises 404
    with pytest.raises(HTTPException) as exc_info:
        assert_can_view_emergency(test_users["responder_a"], sample_emergency, db_session)
    assert exc_info.value.status_code == 404

    # 4. Responder after receiving offer: permitted
    offer = DispatchOffer(
        emergency_id=sample_emergency.id,
        track="community",
        target_kind=TargetKind.RESPONDER.value,
        responder_id=test_users["responder_a"].id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    db_session.add(offer)
    db_session.flush()

    assert_can_view_emergency(test_users["responder_a"], sample_emergency, db_session)

    # 5. Ambulance operator whose unit is offered
    amb_unit = AmbulanceUnit(
        callsign="AMB-01",
        operator_user_id=test_users["operator_a"].id,
        lat=18.5204,
        lng=73.8567,
        base_name="Base 1",
        demo_session_id=test_users["session_1"],
    )
    db_session.add(amb_unit)
    db_session.flush()

    amb_offer = DispatchOffer(
        emergency_id=sample_emergency.id,
        track="professional",
        target_kind=TargetKind.AMBULANCE.value,
        ambulance_id=amb_unit.id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    db_session.add(amb_offer)
    db_session.flush()

    assert_can_view_emergency(test_users["operator_a"], sample_emergency, db_session)


def test_offer_action_authorization(db_session, test_users, sample_emergency):
    """Verify users cannot act on offers dispatched to someone else."""
    offer = DispatchOffer(
        emergency_id=sample_emergency.id,
        track="community",
        target_kind=TargetKind.RESPONDER.value,
        responder_id=test_users["responder_a"].id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    db_session.add(offer)
    db_session.flush()

    # Responder A is assigned -> allowed
    assert_can_act_on_offer(test_users["responder_a"], offer, db_session)

    # Responder B is NOT assigned -> 403 FORBIDDEN
    with pytest.raises(HTTPException) as exc_info:
        assert_can_act_on_offer(test_users["responder_b"], offer, db_session)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "FORBIDDEN"

    # Cross-tenant caller -> 404 NOT_FOUND
    with pytest.raises(HTTPException) as exc_info:
        assert_can_act_on_offer(test_users["cross_tenant"], offer, db_session)
    assert exc_info.value.status_code == 404


def test_medical_profile_consent_gating(db_session, test_users, sample_emergency):
    """Verify medical profile access requires patient consent and accepted offer status."""
    med_profile = MedicalProfile(
        user_id=test_users["citizen_a"].id,
        blood_group="O+",
        allergies=["penicillin"],
        medications=["aspirin"],
        conditions=["hypertension"],
    )
    db_session.add(med_profile)
    db_session.flush()

    # 1. Patient always has access, even when consent_share_medical=False
    sample_emergency.consent_share_medical = False
    db_session.flush()
    assert assert_can_view_medical(test_users["citizen_a"], sample_emergency, med_profile, db_session) is True

    # 2. Responder has NO access when consent is False
    assert assert_can_view_medical(test_users["responder_a"], sample_emergency, med_profile, db_session) is False

    # 3. Patient grants consent: consent_share_medical = True
    sample_emergency.consent_share_medical = True
    db_session.flush()

    # 4. Responder with only OFFERED status still cannot view
    offer = DispatchOffer(
        emergency_id=sample_emergency.id,
        track="community",
        target_kind=TargetKind.RESPONDER.value,
        responder_id=test_users["responder_a"].id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    db_session.add(offer)
    db_session.flush()
    assert assert_can_view_medical(test_users["responder_a"], sample_emergency, med_profile, db_session) is False

    # 5. Once offer is ACCEPTED, responder can view medical profile
    offer.status = OfferStatus.ACCEPTED.value
    db_session.flush()
    assert assert_can_view_medical(test_users["responder_a"], sample_emergency, med_profile, db_session) is True

    # 6. Unrelated Responder B still cannot view
    assert assert_can_view_medical(test_users["responder_b"], sample_emergency, med_profile, db_session) is False
