"""Spatial distance, travel time, and bounding-box mathematics for LIFELINK orchestration."""
import math
from typing import Tuple


EARTH_RADIUS_METERS: float = 6371000.0
METERS_PER_DEGREE_LATITUDE: float = 111320.0


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two geographical points using Haversine formula.
    
    Args:
        lat1: Latitude of point 1 in degrees.
        lng1: Longitude of point 1 in degrees.
        lat2: Latitude of point 2 in degrees.
        lng2: Longitude of point 2 in degrees.
        
    Returns:
        Distance in meters.
    """
    if lat1 == lat2 and lng1 == lng2:
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    # Numerical clamp to prevent domain errors in math.sqrt / atan2
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(EARTH_RADIUS_METERS * c, 2)


def calculate_eta_seconds(
    distance_m: float,
    speed_kmh: float,
    detour_factor: float = 1.35,
    min_seconds: int = 30,
) -> int:
    """Calculate estimated time of arrival in seconds applying detour multiplier and minimum clamp.
    
    Formula:
        speed_mps = speed_kmh * (1000 / 3600)
        eta_s = max(min_seconds, round((distance_m * detour_factor) / speed_mps))
        
    Args:
        distance_m: Straight-line Haversine distance in meters.
        speed_kmh: Expected vehicular or foot response speed in km/h.
        detour_factor: Urban street grid detour factor (default 1.35).
        min_seconds: Minimum response time clamp (default 30 seconds).
        
    Returns:
        Estimated travel time in seconds.
    """
    if distance_m <= 0.0 or speed_kmh <= 0.0:
        return min_seconds

    speed_mps = (speed_kmh * 1000.0) / 3600.0
    effective_distance = distance_m * detour_factor
    travel_time_s = effective_distance / speed_mps

    return max(min_seconds, int(round(travel_time_s)))


def bounding_box_delta_deg(radius_m: float, lat: float) -> Tuple[float, float]:
    """Calculate latitude and longitude degree offsets for SQL bounding-box prefiltering.
    
    Args:
        radius_m: Search radius in meters.
        lat: Latitude of the center point in degrees.
        
    Returns:
        Tuple of (lat_delta_deg, lng_delta_deg).
    """
    if radius_m <= 0.0:
        return (0.0, 0.0)

    lat_delta = radius_m / METERS_PER_DEGREE_LATITUDE

    # Longitude degrees shrink with cosine of latitude; protect against pole division
    lat_rad = math.radians(lat)
    cos_lat = max(0.01, math.cos(lat_rad))
    lng_delta = radius_m / (METERS_PER_DEGREE_LATITUDE * cos_lat)

    return (lat_delta, lng_delta)
