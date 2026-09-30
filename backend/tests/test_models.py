import uuid
from datetime import datetime, timezone, timedelta, date
from app.models import (
    User,
    MedicalProfile,
    ResponderProfile,
    ResponderSkill,
    ResponderCredential,
    AmbulanceUnit,
    Emergency,
    DispatchOffer,
    EmergencyEvent,
    AuditLog,
    DemoSession,
)
from app.domain.enums import (
    UserRole,
    CredentialStatus,
    AmbulanceUnitStatus,
    EmergencyType,
    EmergencyStatus,
    Priority,
    TrackKind,
    OfferStatus,
    AuditOutcome,
)


def test_user_and_medical_profile_creation(db_session):
    demo_session = DemoSession(
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        clock_offset_s=0,
    )
    db_session.add(demo_session)
    db_session.flush()

    user = User(
        email="aarav.patel@example.com",
        password_hash="argon2_fake_hash_value",
        full_name="Aarav Patel",
        phone="+919876543210",
        role=UserRole.CITIZEN.value,
        demo_session_id=demo_session.id,
    )
    db_session.add(user)
    db_session.flush()

    med_profile = MedicalProfile(
        user_id=user.id,
        blood_group="O+",
        allergies="penicillin, peanuts",
        conditions="asthma",
        medications="albuterol",
        contacts=[{"name": "Meera Patel", "phone": "+919876543299", "relation": "Spouse"}],
        share_during_emergency=True,
    )
    db_session.add(med_profile)
    db_session.flush()

    assert user.id is not None
    assert user.role == UserRole.CITIZEN.value
    assert user.medical_profile is not None
    assert user.medical_profile.blood_group == "O+"
    assert "penicillin" in user.medical_profile.allergies
    assert len(user.medical_profile.contacts) == 1


def test_responder_profile_skills_credentials(db_session):
    demo_session = DemoSession(
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        clock_offset_s=0,
    )
    db_session.add(demo_session)
    db_session.flush()

    user = User(
        email="vikram.rao@example.com",
        password_hash="argon2_fake_hash_value",
        full_name="Dr. Vikram Rao",
        phone="+919876543211",
        role=UserRole.RESPONDER.value,
        demo_session_id=demo_session.id,
    )
    db_session.add(user)
    db_session.flush()

    profile = ResponderProfile(
        user_id=user.id,
        category="doctor",
        readiness="available",
        service_radius_m=4000,
        last_lat=18.5210,
        last_lng=73.8570,
        acceptance_rate=0.98,
        responses_24h=2,
    )
    db_session.add(profile)
    db_session.flush()

    skill = ResponderSkill(
        responder_id=user.id,
        skill_code="cpr_aed",
        level=3,
    )
    db_session.add(skill)

    cred = ResponderCredential(
        responder_id=user.id,
        credential_type="MEDICAL_COUNCIL_REG",
        issuer="Maharashtra Medical Council",
        reference_no="MMC-2018-99881",
        expires_on=date(2028, 12, 31),
        status=CredentialStatus.VERIFIED.value,
        reviewed_by=user.id,
        review_note="Verified against council registry",
    )
    db_session.add(cred)
    db_session.flush()

    assert user.responder_profile is not None
    assert user.responder_profile.readiness == "available"
    assert len(user.skills) == 1
    assert user.skills[0].skill_code == "cpr_aed"
    assert len(user.credentials) == 1
    assert user.credentials[0].status == CredentialStatus.VERIFIED.value


def test_emergency_and_dispatch_lifecycle_entities(db_session):
    demo_session = DemoSession(
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        clock_offset_s=0,
    )
    db_session.add(demo_session)
    db_session.flush()

    reporter = User(
        email="kavita.iyer@example.com",
        password_hash="argon2_fake_hash_value",
        full_name="Kavita Iyer",
        phone="+919876543212",
        role=UserRole.CITIZEN.value,
        demo_session_id=demo_session.id,
    )
    responder_user = User(
        email="ravi.kumar@example.com",
        password_hash="argon2_fake_hash_value",
        full_name="Ravi Kumar",
        phone="+919876543213",
        role=UserRole.RESPONDER.value,
        demo_session_id=demo_session.id,
    )
    db_session.add_all([reporter, responder_user])
    db_session.flush()

    ambulance = AmbulanceUnit(
        callsign="AMB-PUNE-01",
        unit_type="advanced",
        status=AmbulanceUnitStatus.AVAILABLE.value,
        lat=18.5300,
        lng=73.8600,
        base_name="Sassoon General Hospital",
        demo_session_id=demo_session.id,
    )
    db_session.add(ambulance)
    db_session.flush()

    emergency = Emergency(
        patient_user_id=reporter.id,
        reported_by_user_id=reporter.id,
        idempotency_key="idemp-key-test-01",
        status=EmergencyStatus.CREATED.value,
        priority=Priority.P1_CRITICAL.value,
        emergency_type=EmergencyType.UNRESPONSIVE.value,
        triage={"chief_complaint": "Unresponsive elderly male", "breathing": False},
        dispatch_plan={"required_skills": ["cpr_aed"], "target_count": 2},
        lat=18.5204,
        lng=73.8567,
        patient_is_reporter=True,
        consent_share_medical=True,
        demo_session_id=demo_session.id,
    )
    db_session.add(emergency)
    db_session.flush()

    offer_community = DispatchOffer(
        emergency_id=emergency.id,
        track=TrackKind.COMMUNITY.value,
        target_kind="responder",
        responder_id=responder_user.id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=90),
        distance_m=350.0,
        eta_s=180,
    )
    offer_pro = DispatchOffer(
        emergency_id=emergency.id,
        track=TrackKind.PROFESSIONAL.value,
        target_kind="ambulance",
        ambulance_id=ambulance.id,
        rank=1,
        status=OfferStatus.OFFERED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=120),
        distance_m=1200.0,
        eta_s=420,
    )
    db_session.add_all([offer_community, offer_pro])
    db_session.flush()

    event = EmergencyEvent(
        emergency_id=emergency.id,
        seq=1,
        type="EMERGENCY_REPORTED",
        actor_user_id=reporter.id,
        actor_role=UserRole.CITIZEN.value,
        payload={"note": "Patient collapsed on FC Road"},
        visible_to=["citizen", "responder", "authority"],
    )
    audit = AuditLog(
        actor_user_id=reporter.id,
        actor_role=UserRole.CITIZEN.value,
        action="emergency_create",
        resource_type="emergencies",
        resource_id=str(emergency.id),
        outcome=AuditOutcome.ALLOW.value,
        ip_hash="fake_sha256_hash",
        meta={"priority": Priority.P1_CRITICAL.value},
    )
    db_session.add_all([event, audit])
    db_session.flush()

    assert emergency.id is not None
    assert len(emergency.offers) == 2
    assert len(emergency.events) == 1
    assert emergency.events[0].seq == 1
    assert emergency.patient.full_name == "Kavita Iyer"
