"""Idempotent seed script for LIFELINK taxonomy, demo sessions, and Appendix B personas."""
from datetime import datetime, timezone, timedelta, date
import json
import math
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import uuid
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.domain.enums import (
    UserRole,
    CredentialStatus,
    AmbulanceUnitStatus,
)
from app.models import (
    User,
    MedicalProfile,
    ResponderProfile,
    ResponderSkill,
    ResponderCredential,
    AmbulanceUnit,
    DemoSession,
)

# Precomputed argon2id hash for "LifelinkDemo2026!" (DATA-05, D-18, T-01-05)
DEFAULT_DEMO_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$5SS4swPLX716D4deqaAHyQ$LIIExLQSve59GkOrsPgY680aWx/zqtX+17fXJcl8v8E"
)

TAXONOMY_PATH = Path(__file__).resolve().parent.parent.parent / "shared" / "taxonomy.json"


def calculate_offset_coordinates(
    center_lat: float, center_lng: float, distance_km: float, bearing_deg: float
) -> Tuple[float, float]:
    """Calculate target coordinates at a given distance and bearing using spherical geodesy."""
    R = 6371.0  # Earth radius in kilometers
    lat1 = math.radians(center_lat)
    lng1 = math.radians(center_lng)
    brng = math.radians(bearing_deg)
    d_r = distance_km / R

    lat2 = math.asin(
        math.sin(lat1) * math.cos(d_r) + math.cos(lat1) * math.sin(d_r) * math.cos(brng)
    )
    lng2 = lng1 + math.atan2(
        math.sin(brng) * math.sin(d_r) * math.cos(lat1),
        math.cos(d_r) - math.sin(lat1) * math.sin(lat2),
    )
    return round(math.degrees(lat2), 6), round(math.degrees(lng2), 6)


def seed_taxonomy() -> Dict[str, Any]:
    """Load and validate canonical shared taxonomy."""
    if not TAXONOMY_PATH.exists():
        raise FileNotFoundError(f"Shared taxonomy file not found at {TAXONOMY_PATH}")

    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_keys = {"emergency_types", "conditions", "skills", "responder_categories", "protocol_skill_requirements"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Taxonomy missing required blocks: {missing}")

    return data


RESPONDER_PERSONAS = [
    {
        "key": "asha",
        "email": "asha.nurse@lifelink.demo",
        "full_name": "Asha Shinde",
        "phone": "+919800000001",
        "category": "nurse",
        "readiness": "available",
        "radius_m": 3000,
        "dist_km": 0.8,
        "bearing": 45.0,
        "cred_status": CredentialStatus.VERIFIED.value,
        "skills": [("bleeding_control", 3), ("trauma_response", 3), ("basic_first_aid", 3), ("cpr_aed", 3)],
    },
    {
        "key": "ravi",
        "email": "ravi.paramedic@lifelink.demo",
        "full_name": "Ravi Gaikwad",
        "phone": "+919800000002",
        "category": "paramedic",
        "readiness": "available",
        "radius_m": 5000,
        "dist_km": 1.3,
        "bearing": 90.0,
        "cred_status": CredentialStatus.VERIFIED.value,
        "skills": [("advanced_life_support", 3), ("trauma_response", 3), ("bleeding_control", 3), ("cpr_aed", 3)],
    },
    {
        "key": "meera",
        "email": "meera.fa@lifelink.demo",
        "full_name": "Meera Kulkarni",
        "phone": "+919800000003",
        "category": "certified_first_aider",
        "readiness": "available",
        "radius_m": 3000,
        "dist_km": 2.1,
        "bearing": 135.0,
        "cred_status": CredentialStatus.VERIFIED.value,
        "skills": [("basic_first_aid", 2), ("cpr_aed", 2), ("bleeding_control", 2)],
    },
    {
        "key": "karan",
        "email": "karan.student@lifelink.demo",
        "full_name": "Karan Joshi",
        "phone": "+919800000004",
        "category": "student_responder",
        "readiness": "available",
        "radius_m": 2000,
        "dist_km": 0.3,
        "bearing": 0.0,
        "cred_status": CredentialStatus.VERIFIED.value,
        "skills": [("cpr_aed", 1)],
    },
    {
        "key": "dr_iyer",
        "email": "dr.iyer@lifelink.demo",
        "full_name": "Dr. Subhash Iyer",
        "phone": "+919800000005",
        "category": "doctor",
        "readiness": "busy",
        "radius_m": 4000,
        "dist_km": 0.6,
        "bearing": 270.0,
        "cred_status": CredentialStatus.VERIFIED.value,
        "skills": [("advanced_life_support", 3), ("trauma_response", 3)],
    },
    {
        "key": "sana",
        "email": "sana.emt@lifelink.demo",
        "full_name": "Sana Khan",
        "phone": "+919800000006",
        "category": "emt",
        "readiness": "available",
        "radius_m": 3000,
        "dist_km": 4.5,
        "bearing": 225.0,
        "cred_status": CredentialStatus.VERIFIED.value,
        "skills": [("trauma_response", 2), ("bleeding_control", 2)],
    },
    {
        "key": "vik",
        "email": "vik.volunteer@lifelink.demo",
        "full_name": "Vikram Jadhav",
        "phone": "+919800000007",
        "category": "medical_volunteer",
        "readiness": "off_duty",
        "radius_m": 2500,
        "dist_km": 1.0,
        "bearing": 315.0,
        "cred_status": CredentialStatus.VERIFIED.value,
        "skills": [("basic_first_aid", 2)],
    },
    {
        "key": "nita",
        "email": "nita.nurse@lifelink.demo",
        "full_name": "Nita Deshmukh",
        "phone": "+919800000008",
        "category": "nurse",
        "readiness": "available",
        "radius_m": 3000,
        "dist_km": 0.9,
        "bearing": 180.0,
        "cred_status": CredentialStatus.EXPIRED.value,
        "skills": [("bleeding_control", 3)],
    },
    {
        "key": "omar",
        "email": "omar.paramedic@lifelink.demo",
        "full_name": "Omar Shaikh",
        "phone": "+919800000009",
        "category": "paramedic",
        "readiness": "available",
        "radius_m": 3500,
        "dist_km": 0.7,
        "bearing": 210.0,
        "cred_status": CredentialStatus.PENDING.value,
        "skills": [("trauma_response", 3)],
    },
    {
        "key": "dev",
        "email": "dev.doctor@lifelink.demo",
        "full_name": "Dr. Devendra More",
        "phone": "+919800000010",
        "category": "doctor",
        "readiness": "available",
        "radius_m": 5000,
        "dist_km": 1.8,
        "bearing": 160.0,
        "cred_status": CredentialStatus.VERIFIED.value,
        "skills": [("advanced_life_support", 3), ("cpr_aed", 3)],
    },
]

AMBULANCE_UNITS = [
    {
        "callsign": "AMB-01",
        "unit_type": "advanced",
        "status": AmbulanceUnitStatus.AVAILABLE.value,
        "dist_km": 2.4,
        "bearing": 330.0,
        "base_name": "Sassoon General Hospital Base",
    },
    {
        "callsign": "AMB-02",
        "unit_type": "basic",
        "status": AmbulanceUnitStatus.AVAILABLE.value,
        "dist_km": 3.9,
        "bearing": 60.0,
        "base_name": "KEM Hospital Pune Base",
    },
    {
        "callsign": "AMB-03",
        "unit_type": "basic",
        "status": AmbulanceUnitStatus.BUSY.value,
        "dist_km": 1.1,
        "bearing": 195.0,
        "base_name": "Ruby Hall Clinic Base",
    },
]


def seed_personas(session_id: Optional[uuid.UUID] = None, db: Optional[Session] = None) -> None:
    """Seed or update personas and ambulances idempotently for a given demo session."""
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        center_lat = settings.DEMO_CENTER_LAT
        center_lng = settings.DEMO_CENTER_LNG

        # 1. Authority User
        authority = db.query(User).filter(User.email == "authority.demo@lifelink.demo").first()
        if not authority:
            authority = User(
                email="authority.demo@lifelink.demo",
                password_hash=DEFAULT_DEMO_PASSWORD_HASH,
                full_name="Chief Inspector Rao",
                role=UserRole.AUTHORITY.value,
                phone="+919800000098",
                demo_session_id=session_id,
            )
            db.add(authority)
        else:
            authority.full_name = "Chief Inspector Rao"
            authority.role = UserRole.AUTHORITY.value
            authority.demo_session_id = session_id
        db.flush()

        # 2. Ambulance Operator User
        operator = db.query(User).filter(User.email == "operator.demo@lifelink.demo").first()
        if not operator:
            operator = User(
                email="operator.demo@lifelink.demo",
                password_hash=DEFAULT_DEMO_PASSWORD_HASH,
                full_name="Dispatcher Deshmukh",
                role=UserRole.AMBULANCE_OPERATOR.value,
                phone="+919800000099",
                demo_session_id=session_id,
            )
            db.add(operator)
        else:
            operator.full_name = "Dispatcher Deshmukh"
            operator.role = UserRole.AMBULANCE_OPERATOR.value
            operator.demo_session_id = session_id
        db.flush()

        # 3. Citizen Demo User + Medical Profile
        citizen = db.query(User).filter(User.email == "citizen.demo@lifelink.demo").first()
        if not citizen:
            citizen = User(
                email="citizen.demo@lifelink.demo",
                password_hash=DEFAULT_DEMO_PASSWORD_HASH,
                full_name="Aarav Sharma",
                role=UserRole.CITIZEN.value,
                phone="+919800000000",
                demo_session_id=session_id,
            )
            db.add(citizen)
            db.flush()
        else:
            citizen.full_name = "Aarav Sharma"
            citizen.demo_session_id = session_id
            db.flush()

        med = db.query(MedicalProfile).filter(MedicalProfile.user_id == citizen.id).first()
        if not med:
            med = MedicalProfile(
                user_id=citizen.id,
                blood_group="B+",
                allergies="Peanuts",
                conditions="Mild Asthma",
                medications="Albuterol inhaler as needed",
                contacts=[{"name": "Ananya Sharma", "phone": "+919800000090", "relation": "Spouse"}],
                share_during_emergency=True,
            )
            db.add(med)
        else:
            med.blood_group = "B+"
            med.allergies = "Peanuts"
            med.conditions = "Mild Asthma"
            med.medications = "Albuterol inhaler as needed"
            med.share_during_emergency = True
        db.flush()

        # 4. Responder Personas
        for p in RESPONDER_PERSONAS:
            email = p["email"]
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    password_hash=DEFAULT_DEMO_PASSWORD_HASH,
                    full_name=p["full_name"],
                    role=UserRole.RESPONDER.value,
                    phone=p["phone"],
                    demo_session_id=session_id,
                )
                db.add(user)
                db.flush()
            else:
                user.full_name = p["full_name"]
                user.role = UserRole.RESPONDER.value
                user.phone = p["phone"]
                user.demo_session_id = session_id
                db.flush()

            # Coordinates
            lat, lng = calculate_offset_coordinates(center_lat, center_lng, p["dist_km"], p["bearing"])

            # Profile
            profile = db.query(ResponderProfile).filter(ResponderProfile.user_id == user.id).first()
            if not profile:
                profile = ResponderProfile(
                    user_id=user.id,
                    category=p["category"],
                    readiness=p["readiness"],
                    service_radius_m=p["radius_m"],
                    last_lat=lat,
                    last_lng=lng,
                    pinned_location=True,
                    acceptance_rate=0.95,
                    responses_24h=1,
                )
                db.add(profile)
            else:
                profile.category = p["category"]
                profile.readiness = p["readiness"]
                profile.service_radius_m = p["radius_m"]
                profile.last_lat = lat
                profile.last_lng = lng
                profile.pinned_location = True
            db.flush()

            # Skills
            # Cleanly replace existing skills for this responder
            db.query(ResponderSkill).filter(ResponderSkill.responder_id == user.id).delete()
            for skill_code, level in p["skills"]:
                db.add(ResponderSkill(responder_id=user.id, skill_code=skill_code, level=level))
            db.flush()

            # Credential
            cred = db.query(ResponderCredential).filter(ResponderCredential.responder_id == user.id).first()
            expires_date = date(2028, 12, 31) if p["cred_status"] != CredentialStatus.EXPIRED.value else date(2025, 1, 1)
            if not cred:
                cred = ResponderCredential(
                    responder_id=user.id,
                    credential_type=f"{p['category'].upper()}_LICENSE",
                    issuer="Maharashtra State Medical Authority",
                    reference_no=f"REG-2024-{p['key'].upper()}",
                    expires_on=expires_date,
                    status=p["cred_status"],
                    reviewed_by=authority.id if p["cred_status"] == CredentialStatus.VERIFIED.value else None,
                    review_note="System verified seeded demo credential",
                )
                db.add(cred)
            else:
                cred.status = p["cred_status"]
                cred.expires_on = expires_date
                cred.reviewed_by = authority.id if p["cred_status"] == CredentialStatus.VERIFIED.value else None
            db.flush()

        # 5. Ambulance Units
        for amb in AMBULANCE_UNITS:
            callsign = amb["callsign"]
            a_lat, a_lng = calculate_offset_coordinates(center_lat, center_lng, amb["dist_km"], amb["bearing"])
            unit = (
                db.query(AmbulanceUnit)
                .filter(AmbulanceUnit.callsign == callsign, AmbulanceUnit.demo_session_id == session_id)
                .first()
            )
            if not unit:
                unit = AmbulanceUnit(
                    callsign=callsign,
                    unit_type=amb["unit_type"],
                    status=amb["status"],
                    lat=a_lat,
                    lng=a_lng,
                    base_name=amb["base_name"],
                    operator_user_id=operator.id,
                    demo_session_id=session_id,
                )
                db.add(unit)
            else:
                unit.unit_type = amb["unit_type"]
                unit.status = amb["status"]
                unit.lat = a_lat
                unit.lng = a_lng
                unit.base_name = amb["base_name"]
                unit.operator_user_id = operator.id
            db.flush()

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()


def seed_all() -> None:
    """Run full idempotent provisioning of taxonomy, default demo session, and demo personas."""
    db = SessionLocal()
    try:
        # 1. Validate taxonomy
        seed_taxonomy()

        # 2. Provision default demo session
        default_session_id = uuid.UUID(settings.DEFAULT_DEMO_SESSION_ID)
        session = db.query(DemoSession).filter(DemoSession.id == default_session_id).first()
        if not session:
            session = DemoSession(
                id=default_session_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                clock_offset_s=0,
                scenario={"name": "pune_golden_hour_demo"},
                is_active=True,
            )
            db.add(session)
            db.commit()

        # 3. Seed personas scoped to default demo session
        seed_personas(session_id=default_session_id, db=db)
        print("Idempotent seed completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
