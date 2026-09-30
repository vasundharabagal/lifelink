"""Integration tests for deterministic location privacy tier filtering (Spec §11.1, CORE-07)."""
import uuid
import pytest
from app.domain.enums import OfferStatus, UserRole
from app.models.emergency import DispatchOffer, Emergency
from app.models.user import User
from app.orchestration.distance import haversine_distance_m
from app.services.privacy import (
    calculate_coarse_coordinates,
    filter_emergency_location_for_user,
)


def test_coarse_coordinates_offset_distance():
    """Verify coarse coordinates are displaced by ~200-300m (mean ~250m) from exact location (CORE-07, D-08)."""
    exact_lat = 18.5204
    exact_lng = 73.8567
    incident_id = uuid.uuid4()

    coarse_lat, coarse_lng = calculate_coarse_coordinates(exact_lat, exact_lng, incident_id)

    dist_m = haversine_distance_m(exact_lat, exact_lng, coarse_lat, coarse_lng)

    # Offset must be between 195m and 305m
    assert 195.0 <= dist_m <= 305.0


def test_coarse_coordinates_deterministic_stability():
    """Verify coarse hash offset is 100% deterministic and does not jitter across polls (D-09)."""
    exact_lat = 18.5204
    exact_lng = 73.8567
    incident_id = uuid.uuid4()

    first_result = calculate_coarse_coordinates(exact_lat, exact_lng, incident_id)

    # Repeat 50 times
    for _ in range(50):
        subsequent = calculate_coarse_coordinates(exact_lat, exact_lng, incident_id)
        assert subsequent == first_result

    # Different incident must produce distinct offset
    other_incident = uuid.uuid4()
    other_result = calculate_coarse_coordinates(exact_lat, exact_lng, other_incident)
    assert other_result != first_result


def test_privacy_tier_filtering_roles_and_states():
    """Verify location privacy tiers for reporter, authority, offered, accepted, and revoked responders (CORE-07, D-10)."""
    reporter_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    authority_id = uuid.uuid4()
    responder_id = uuid.uuid4()
    emergency_id = uuid.uuid4()

    exact_lat = 18.5204
    exact_lng = 73.8567

    emergency = Emergency(
        id=emergency_id,
        reported_by_user_id=reporter_id,
        patient_user_id=patient_id,
        lat=exact_lat,
        lng=exact_lng,
    )

    reporter = User(id=reporter_id, role=UserRole.CITIZEN.value)
    patient = User(id=patient_id, role=UserRole.CITIZEN.value)
    authority = User(id=authority_id, role=UserRole.AUTHORITY.value)
    responder = User(id=responder_id, role=UserRole.RESPONDER.value)

    # 1. Reporter and patient get exact coordinates
    r_lat, r_lng, r_tier, r_rev = filter_emergency_location_for_user(emergency, reporter)
    assert (r_lat, r_lng, r_tier, r_rev) == (exact_lat, exact_lng, "exact", False)

    p_lat, p_lng, p_tier, p_rev = filter_emergency_location_for_user(emergency, patient)
    assert (p_lat, p_lng, p_tier, p_rev) == (exact_lat, exact_lng, "exact", False)

    # 2. Authority gets exact coordinates
    a_lat, a_lng, a_tier, a_rev = filter_emergency_location_for_user(emergency, authority)
    assert (a_lat, a_lng, a_tier, a_rev) == (exact_lat, exact_lng, "exact", False)

    # 3. Responder with OFFERED status gets coarse coordinates
    offer_offered = DispatchOffer(
        id=uuid.uuid4(),
        emergency_id=emergency_id,
        responder_id=responder_id,
        status=OfferStatus.OFFERED.value,
    )
    o_lat, o_lng, o_tier, o_rev = filter_emergency_location_for_user(emergency, responder, offer_offered)
    assert o_tier == "coarse"
    assert o_rev is False
    assert (o_lat, o_lng) != (exact_lat, exact_lng)
    assert 195.0 <= haversine_distance_m(exact_lat, exact_lng, o_lat, o_lng) <= 305.0

    # 4. Responder with ACCEPTED status gets exact coordinates
    offer_accepted = DispatchOffer(
        id=uuid.uuid4(),
        emergency_id=emergency_id,
        responder_id=responder_id,
        status=OfferStatus.ACCEPTED.value,
    )
    acc_lat, acc_lng, acc_tier, acc_rev = filter_emergency_location_for_user(emergency, responder, offer_accepted)
    assert (acc_lat, acc_lng, acc_tier, acc_rev) == (exact_lat, exact_lng, "exact", False)

    # 5. Responder with ARRIVED status gets exact coordinates
    offer_arrived = DispatchOffer(
        id=uuid.uuid4(),
        emergency_id=emergency_id,
        responder_id=responder_id,
        status=OfferStatus.ARRIVED.value,
    )
    arr_lat, arr_lng, arr_tier, arr_rev = filter_emergency_location_for_user(emergency, responder, offer_arrived)
    assert (arr_lat, arr_lng, arr_tier, arr_rev) == (exact_lat, exact_lng, "exact", False)

    # 6. Responder with DECLINED, EXPIRED, or COMPLETED status has location revoked (null coordinates)
    for terminal_status in [OfferStatus.DECLINED.value, OfferStatus.EXPIRED.value, OfferStatus.COMPLETED.value]:
        offer_term = DispatchOffer(
            id=uuid.uuid4(),
            emergency_id=emergency_id,
            responder_id=responder_id,
            status=terminal_status,
        )
        term_lat, term_lng, term_tier, term_rev = filter_emergency_location_for_user(emergency, responder, offer_term)
        assert (term_lat, term_lng, term_tier, term_rev) == (None, None, "revoked", True)

    # 7. Responder without any offer gets revoked
    none_lat, none_lng, none_tier, none_rev = filter_emergency_location_for_user(emergency, responder, None)
    assert (none_lat, none_lng, none_tier, none_rev) == (None, None, "revoked", True)
