import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.exc import IntegrityError, InternalError, DBAPIError
from sqlalchemy import text
from app.models import (
    User,
    ResponderProfile,
    ResponderSkill,
    AmbulanceUnit,
    Emergency,
    DispatchOffer,
    EmergencyEvent,
    AuditLog,
    DemoSession,
)
from app.domain.enums import (
    UserRole,
    AmbulanceUnitStatus,
    EmergencyType,
    EmergencyStatus,
    Priority,
    TrackKind,
    OfferStatus,
    AuditOutcome,
)


def _setup_base_entities(db_session):
    demo_session = DemoSession(
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        clock_offset_s=0,
    )
    db_session.add(demo_session)
    db_session.flush()

    patient = User(
        email=f"patient_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="argon2_fake_hash",
        full_name="Patient Test",
        role=UserRole.CITIZEN.value,
        demo_session_id=demo_session.id,
    )
    responder_user = User(
        email=f"resp_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="argon2_fake_hash",
        full_name="Responder Test",
        role=UserRole.RESPONDER.value,
        demo_session_id=demo_session.id,
    )
    db_session.add_all([patient, responder_user])
    db_session.flush()

    responder_profile = ResponderProfile(
        user_id=responder_user.id,
        category="emt",
        readiness="available",
    )
    ambulance = AmbulanceUnit(
        callsign=f"AMB_{uuid.uuid4().hex[:6]}",
        lat=18.52,
        lng=73.85,
        base_name="Base 1",
        demo_session_id=demo_session.id,
    )
    db_session.add_all([responder_profile, ambulance])
    db_session.flush()

    emergency1 = Emergency(
        patient_user_id=patient.id,
        reported_by_user_id=patient.id,
        idempotency_key=f"idemp_{uuid.uuid4()}",
        status=EmergencyStatus.ACTIVE.value if hasattr(EmergencyStatus, 'ACTIVE') else "DISPATCHING",
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.CHEST_PAIN.value,
        triage={"symptom": "chest pain"},
        dispatch_plan={},
        lat=18.5204,
        lng=73.8567,
        demo_session_id=demo_session.id,
    )
    db_session.add(emergency1)
    db_session.flush()

    return demo_session, patient, responder_user, ambulance, emergency1


def test_uq_offers_active_responder(db_session):
    """Verify partial unique index prevents a responder from receiving two active offers simultaneously."""
    demo_session, patient, responder_user, ambulance, emergency1 = _setup_base_entities(db_session)

    emergency2 = Emergency(
        patient_user_id=patient.id,
        reported_by_user_id=patient.id,
        idempotency_key=f"idemp_{uuid.uuid4()}",
        status=EmergencyStatus.COMPLETED.value,  # inactive so patient can be reused
        priority=Priority.P2_SERIOUS.value,
        emergency_type=EmergencyType.BURNS.value,
        triage={},
        dispatch_plan={},
        lat=18.5204,
        lng=73.8567,
        demo_session_id=demo_session.id,
    )
    db_session.add(emergency2)
    db_session.flush()

    offer1 = DispatchOffer(
        emergency_id=emergency1.id,
        track=TrackKind.COMMUNITY.value,
        target_kind="responder",
        responder_id=responder_user.id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=60),
    )
    db_session.add(offer1)
    db_session.flush()

    # Second active offer to same responder should violate uq_offers_active_responder
    offer2 = DispatchOffer(
        emergency_id=emergency2.id,
        track=TrackKind.COMMUNITY.value,
        target_kind="responder",
        responder_id=responder_user.id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=60),
    )
    db_session.add(offer2)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()
    assert "uq_offers_active_responder" in str(exc_info.value).lower()


def test_uq_offers_active_ambulance(db_session):
    """Verify partial unique index prevents an ambulance from receiving two active offers."""
    demo_session, patient, responder_user, ambulance, emergency1 = _setup_base_entities(db_session)

    emergency2 = Emergency(
        patient_user_id=patient.id,
        reported_by_user_id=patient.id,
        idempotency_key=f"idemp_{uuid.uuid4()}",
        status=EmergencyStatus.COMPLETED.value,
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.SEIZURE.value,
        triage={},
        dispatch_plan={},
        lat=18.5204,
        lng=73.8567,
        demo_session_id=demo_session.id,
    )
    db_session.add(emergency2)
    db_session.flush()

    offer1 = DispatchOffer(
        emergency_id=emergency1.id,
        track=TrackKind.PROFESSIONAL.value,
        target_kind="ambulance",
        ambulance_id=ambulance.id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=120),
    )
    db_session.add(offer1)
    db_session.flush()

    offer2 = DispatchOffer(
        emergency_id=emergency2.id,
        track=TrackKind.PROFESSIONAL.value,
        target_kind="ambulance",
        ambulance_id=ambulance.id,
        rank=1,
        status=OfferStatus.ACCEPTED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=120),
    )
    db_session.add(offer2)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()
    assert "uq_offers_active_ambulance" in str(exc_info.value).lower()


def test_uq_offers_active_track(db_session):
    """Verify single winner concurrency guard per emergency track (uq_offers_active_track)."""
    demo_session, patient, responder1, ambulance, emergency1 = _setup_base_entities(db_session)

    responder2 = User(
        email=f"resp2_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="argon2_fake_hash",
        full_name="Responder 2",
        role=UserRole.RESPONDER.value,
        demo_session_id=demo_session.id,
    )
    db_session.add(responder2)
    db_session.flush()

    offer1 = DispatchOffer(
        emergency_id=emergency1.id,
        track=TrackKind.COMMUNITY.value,
        target_kind="responder",
        responder_id=responder1.id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=90),
    )
    db_session.add(offer1)
    db_session.flush()

    # Second active offer on same emergency community track
    offer2 = DispatchOffer(
        emergency_id=emergency1.id,
        track=TrackKind.COMMUNITY.value,
        target_kind="responder",
        responder_id=responder2.id,
        rank=2,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=90),
    )
    db_session.add(offer2)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()
    assert "uq_offers_active_track" in str(exc_info.value).lower()


def test_uq_emergencies_active_patient(db_session):
    """Verify patient cannot have more than one non-terminal emergency open at once."""
    demo_session, patient, responder_user, ambulance, emergency1 = _setup_base_entities(db_session)

    emergency2 = Emergency(
        patient_user_id=patient.id,
        reported_by_user_id=patient.id,
        idempotency_key=f"idemp_{uuid.uuid4()}",
        status=EmergencyStatus.TRIAGED.value,
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.TRAUMA_FALL.value,
        triage={},
        dispatch_plan={},
        lat=18.5204,
        lng=73.8567,
        demo_session_id=demo_session.id,
    )
    db_session.add(emergency2)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()
    assert "uq_emergencies_active_patient" in str(exc_info.value).lower()


def test_append_only_trigger_emergency_events_update(db_session):
    """Verify PostgreSQL trigger rejects UPDATE on emergency_events."""
    demo_session, patient, responder_user, ambulance, emergency = _setup_base_entities(db_session)

    event = EmergencyEvent(
        emergency_id=emergency.id,
        seq=1,
        type="EMERGENCY_REPORTED",
        actor_user_id=patient.id,
        actor_role=UserRole.CITIZEN.value,
        payload={"note": "Original timeline entry"},
        visible_to=["citizen"],
    )
    db_session.add(event)
    db_session.flush()

    # Attempt UPDATE via raw SQL to trigger PostgreSQL trigger directly
    with pytest.raises((InternalError, DBAPIError)) as exc_update:
        db_session.execute(
            text("UPDATE emergency_events SET payload = :p WHERE id = :id"),
            {"p": '{"note": "tampered"}', "id": event.id},
        )
        db_session.flush()
    assert "append-only" in str(exc_update.value).lower()


def test_append_only_trigger_emergency_events_delete(db_session):
    """Verify PostgreSQL trigger rejects DELETE on emergency_events."""
    demo_session, patient, responder_user, ambulance, emergency = _setup_base_entities(db_session)

    event = EmergencyEvent(
        emergency_id=emergency.id,
        seq=1,
        type="EMERGENCY_REPORTED",
        actor_user_id=patient.id,
        actor_role=UserRole.CITIZEN.value,
        payload={"note": "Original timeline entry"},
        visible_to=["citizen"],
    )
    db_session.add(event)
    db_session.flush()

    # Attempt DELETE via raw SQL
    with pytest.raises((InternalError, DBAPIError)) as exc_delete:
        db_session.execute(
            text("DELETE FROM emergency_events WHERE id = :id"),
            {"id": event.id},
        )
        db_session.flush()
    assert "append-only" in str(exc_delete.value).lower()


def test_append_only_trigger_audit_logs_update(db_session):
    """Verify PostgreSQL trigger rejects UPDATE on audit_logs."""
    demo_session, patient, responder_user, ambulance, emergency = _setup_base_entities(db_session)

    audit = AuditLog(
        actor_user_id=patient.id,
        actor_role=UserRole.CITIZEN.value,
        action="emergency_create",
        resource_type="emergencies",
        resource_id=str(emergency.id),
        outcome=AuditOutcome.ALLOW.value,
        ip_hash="sha256_audit_hash",
        meta={"auth": "ok"},
    )
    db_session.add(audit)
    db_session.flush()

    # Attempt UPDATE
    with pytest.raises((InternalError, DBAPIError)) as exc_update:
        db_session.execute(
            text("UPDATE audit_logs SET outcome = :o WHERE id = :id"),
            {"o": "deny", "id": audit.id},
        )
        db_session.flush()
    assert "append-only" in str(exc_update.value).lower()


def test_append_only_trigger_audit_logs_delete(db_session):
    """Verify PostgreSQL trigger rejects DELETE on audit_logs."""
    demo_session, patient, responder_user, ambulance, emergency = _setup_base_entities(db_session)

    audit = AuditLog(
        actor_user_id=patient.id,
        actor_role=UserRole.CITIZEN.value,
        action="emergency_create",
        resource_type="emergencies",
        resource_id=str(emergency.id),
        outcome=AuditOutcome.ALLOW.value,
        ip_hash="sha256_audit_hash",
        meta={"auth": "ok"},
    )
    db_session.add(audit)
    db_session.flush()

    # Attempt DELETE
    with pytest.raises((InternalError, DBAPIError)) as exc_delete:
        db_session.execute(
            text("DELETE FROM audit_logs WHERE id = :id"),
            {"id": audit.id},
        )
        db_session.flush()
    assert "append-only" in str(exc_delete.value).lower()


def test_check_constraint_skill_level(db_session):
    """Verify skill level must be between 1 and 3."""
    demo_session, patient, responder_user, ambulance, emergency = _setup_base_entities(db_session)

    invalid_skill = ResponderSkill(
        responder_id=responder_user.id,
        skill_code="cpr_aed",
        level=4,  # Invalid: must be 1..3
    )
    db_session.add(invalid_skill)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()
    assert "ck_responder_skills_level" in str(exc_info.value).lower()
