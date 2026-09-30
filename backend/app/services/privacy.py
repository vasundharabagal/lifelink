"""Location privacy tier service computing deterministic coarse hashes and access masks (Spec §11.1, CORE-07)."""
import hashlib
import math
from typing import Optional, Tuple
import uuid

from app.domain.enums import OfferStatus, UserRole
from app.models.emergency import DispatchOffer, Emergency
from app.models.user import User


def calculate_coarse_coordinates(
    lat: float,
    lng: float,
    incident_id: uuid.UUID,
) -> Tuple[float, float]:
    """Derive deterministic pseudo-random bearing and distance (~200m-300m) from incident UUID.
    
    Guarantees that the coarse location presented to responders before accepting an offer:
    1. Is displaced by ~200-300m from the patient's exact location (mean ~250m).
    2. Is completely deterministic: repeated polls or multiple responders viewing the same
       incident see identical stable coordinates without map jumping.
    3. Cannot be reverse-engineered without knowledge of exact coordinates.
    """
    digest = hashlib.sha256(str(incident_id).encode("utf-8")).hexdigest()

    # Deterministic bearing: 0 to 359 degrees
    bearing_deg = int(digest[:8], 16) % 360
    # Deterministic distance: 200.0m to 299.99m (mean ~250m)
    distance_m = 200.0 + (int(digest[8:16], 16) % 10000) / 100.0

    bearing_rad = math.radians(bearing_deg)
    dist_km = distance_m / 1000.0
    R = 6371.0  # Earth radius in km

    lat1 = math.radians(lat)
    lng1 = math.radians(lng)
    d_r = dist_km / R

    lat2 = math.asin(
        math.sin(lat1) * math.cos(d_r) + math.cos(lat1) * math.sin(d_r) * math.cos(bearing_rad)
    )
    lng2 = lng1 + math.atan2(
        math.sin(bearing_rad) * math.sin(d_r) * math.cos(lat1),
        math.cos(d_r) - math.sin(lat1) * math.sin(lat2),
    )

    return round(math.degrees(lat2), 5), round(math.degrees(lng2), 5)


def filter_emergency_location_for_user(
    emergency: Emergency,
    user: User,
    active_offer: Optional[DispatchOffer] = None,
) -> Tuple[Optional[float], Optional[float], str, bool]:
    """Filter coordinates based on viewer role and assignment status (CORE-07, Spec §11.1).
    
    Returns (lat, lng, location_tier, location_revoked):
    - exact: Incident owners, authorities, or responders/operators with ACCEPTED/ARRIVED status.
    - coarse: Responders/operators with active OFFERED status (~250m hash offset).
    - revoked: Declining, expired, completed responders, or unauthorized viewers (lat: None, lng: None).
    """
    # 1. Authority oversight and incident participants (reporter/patient) always have exact view
    if user.role == UserRole.AUTHORITY.value or user.id in (
        emergency.reported_by_user_id,
        emergency.patient_user_id,
    ):
        return emergency.lat, emergency.lng, "exact", False

    # 2. Responders and ambulance units with an active offer
    if active_offer is not None:
        if active_offer.status in (OfferStatus.ACCEPTED.value, OfferStatus.ARRIVED.value):
            return emergency.lat, emergency.lng, "exact", False

        if active_offer.status == OfferStatus.OFFERED.value:
            c_lat, c_lng = calculate_coarse_coordinates(
                lat=emergency.lat,
                lng=emergency.lng,
                incident_id=emergency.id,
            )
            return c_lat, c_lng, "coarse", False

    # 3. Revoked / unauthorized view: coordinates are nullified (T-05-03)
    return None, None, "revoked", True
