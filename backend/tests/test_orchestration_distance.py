"""Unit tests for spatial distance, ETA calculation, and bounding box math."""
import pytest
from app.orchestration.distance import (
    haversine_distance_m,
    calculate_eta_seconds,
    bounding_box_delta_deg,
    EARTH_RADIUS_METERS,
)


def test_haversine_identical_points():
    """Identical coordinates should return exactly 0.0 meters."""
    dist = haversine_distance_m(18.5204, 73.8567, 18.5204, 73.8567)
    assert dist == 0.0


def test_haversine_known_distance():
    """Test Haversine distance against known reference offset (~800m)."""
    # DEMO_CENTER is Pune (18.5204, 73.8567)
    # Point ~800m away at bearing 45 deg: ~ (18.5255, 73.8620)
    lat1, lng1 = 18.5204, 73.8567
    lat2, lng2 = 18.5255, 73.8620
    dist = haversine_distance_m(lat1, lng1, lat2, lng2)
    # Distance should be between 750m and 850m
    assert 750.0 <= dist <= 850.0


def test_haversine_quarter_earth():
    """Distance between equator and North pole should approximate pi/2 * R."""
    dist = haversine_distance_m(0.0, 0.0, 90.0, 0.0)
    expected = (3.141592653589793 / 2.0) * EARTH_RADIUS_METERS
    assert abs(dist - expected) < 1000.0  # within 1km on global scale


def test_calculate_eta_bounds_and_clamp():
    """Test ETA calculation clamping at 30s minimum."""
    # Zero or tiny distance clamps to min_seconds (30s)
    eta_zero = calculate_eta_seconds(0.0, speed_kmh=25.0)
    assert eta_zero == 30

    eta_tiny = calculate_eta_seconds(10.0, speed_kmh=25.0)
    assert eta_tiny == 30

    # Test normal distance: 1000m at 25km/h (~6.94 m/s) with 1.35 detour
    # effective_distance = 1350m / 6.944 m/s ~= 194.4s -> 194s
    eta_normal = calculate_eta_seconds(1000.0, speed_kmh=25.0, detour_factor=1.35)
    assert 190 <= eta_normal <= 200

    # Test ambulance speed: 1000m at 35km/h (~9.72 m/s) with 1.35 detour
    # effective_distance = 1350m / 9.722 m/s ~= 138.8s -> 139s
    eta_amb = calculate_eta_seconds(1000.0, speed_kmh=35.0, detour_factor=1.35)
    assert 135 <= eta_amb <= 145


def test_bounding_box_delta_deg():
    """Verify bounding box degree deltas enclose the target radius."""
    lat = 18.5204
    radius_m = 3000.0
    lat_delta, lng_delta = bounding_box_delta_deg(radius_m, lat)

    # 3000m / 111320m/deg ~= 0.0269 deg latitude
    assert 0.026 <= lat_delta <= 0.028

    # Longitude delta at lat=18.52 should be slightly larger than lat_delta (cos(18.52) ~= 0.948)
    # 0.0269 / 0.948 ~= 0.0284 deg
    assert lng_delta > lat_delta
    assert 0.027 <= lng_delta <= 0.030

    # Verify points on northern and eastern boundary have distance <= radius_m (approx)
    dist_north = haversine_distance_m(lat, 73.8567, lat + lat_delta, 73.8567)
    assert abs(dist_north - radius_m) < 10.0

    dist_east = haversine_distance_m(lat, 73.8567, lat, 73.8567 + lng_delta)
    assert abs(dist_east - radius_m) < 10.0


def test_bounding_box_zero_radius():
    """Zero radius returns 0.0 deltas."""
    assert bounding_box_delta_deg(0.0, 18.5204) == (0.0, 0.0)
    assert bounding_box_delta_deg(-100.0, 18.5204) == (0.0, 0.0)
