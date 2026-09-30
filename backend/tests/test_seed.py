import math
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import pytest
from app.core.config import settings
from app.core.db import SessionLocal
from app.models import User, ResponderProfile, AmbulanceUnit, MedicalProfile
from app.seed import seed_all, DEFAULT_DEMO_PASSWORD_HASH


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Standard Haversine formula returning distance in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def test_seed_persona_counts_and_roles():
    """Verify seed_all creates exact Appendix B persona cast."""
    seed_all()
    db = SessionLocal()
    try:
        responders = db.query(ResponderProfile).all()
        assert len(responders) == 10

        ambulances = db.query(AmbulanceUnit).all()
        assert len(ambulances) == 3

        callsigns = {a.callsign for a in ambulances}
        assert callsigns == {"AMB-01", "AMB-02", "AMB-03"}

        citizen = db.query(User).filter(User.email == "citizen.demo@lifelink.demo").first()
        assert citizen is not None
        assert citizen.medical_profile is not None
        assert citizen.medical_profile.share_during_emergency is True
        assert citizen.medical_profile.blood_group == "B+"
    finally:
        db.close()


def test_seed_geographic_distances():
    """Verify dynamic offset coordinate calculations match Appendix B distances."""
    seed_all()
    db = SessionLocal()
    try:
        center_lat = settings.DEMO_CENTER_LAT
        center_lng = settings.DEMO_CENTER_LNG

        # 1. Asha: target 0.8 km
        asha_user = db.query(User).filter(User.email == "asha.nurse@lifelink.demo").first()
        assert asha_user is not None
        asha_dist = haversine_km(center_lat, center_lng, asha_user.responder_profile.last_lat, asha_user.responder_profile.last_lng)
        assert 0.75 <= asha_dist <= 0.85

        # 2. Ravi: target 1.3 km
        ravi_user = db.query(User).filter(User.email == "ravi.paramedic@lifelink.demo").first()
        assert ravi_user is not None
        ravi_dist = haversine_km(center_lat, center_lng, ravi_user.responder_profile.last_lat, ravi_user.responder_profile.last_lng)
        assert 1.25 <= ravi_dist <= 1.35

        # 3. Karan: target 0.3 km
        karan_user = db.query(User).filter(User.email == "karan.student@lifelink.demo").first()
        assert karan_user is not None
        karan_dist = haversine_km(center_lat, center_lng, karan_user.responder_profile.last_lat, karan_user.responder_profile.last_lng)
        assert 0.25 <= karan_dist <= 0.35

        # 4. Amb-1: target 2.4 km
        amb1 = db.query(AmbulanceUnit).filter(AmbulanceUnit.callsign == "AMB-01").first()
        assert amb1 is not None
        amb1_dist = haversine_km(center_lat, center_lng, amb1.lat, amb1.lng)
        assert 2.3 <= amb1_dist <= 2.5
    finally:
        db.close()


def test_seed_idempotency():
    """Verify repeated execution of seed_all leaves row counts invariant and raises no errors."""
    seed_all()
    db = SessionLocal()
    try:
        count_users_1 = db.query(User).count()
        count_responders_1 = db.query(ResponderProfile).count()
        count_amb_1 = db.query(AmbulanceUnit).count()
    finally:
        db.close()

    # Second run
    seed_all()
    db = SessionLocal()
    try:
        count_users_2 = db.query(User).count()
        count_responders_2 = db.query(ResponderProfile).count()
        count_amb_2 = db.query(AmbulanceUnit).count()

        assert count_users_1 == count_users_2
        assert count_responders_1 == count_responders_2
        assert count_amb_1 == count_amb_2
    finally:
        db.close()


def test_precomputed_password_hash():
    """Verify precomputed argon2 hash matches standard demo password (DATA-05, T-01-05)."""
    ph = PasswordHasher()
    # Should verify without exception
    assert ph.verify(DEFAULT_DEMO_PASSWORD_HASH, "LifelinkDemo2026!") is True

    # Bad password should raise VerifyMismatchError
    with pytest.raises(VerifyMismatchError):
        ph.verify(DEFAULT_DEMO_PASSWORD_HASH, "WrongPassword123")
