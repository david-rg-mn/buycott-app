from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0
WALKING_SPEED_KMPH = 4.8
DRIVING_SPEED_KMPH = 32.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def _minutes_for_mode(distance_km: float, speed_kmph: float) -> int:
    if distance_km <= 0:
        return 1
    hours = distance_km / speed_kmph
    minutes = max(1, round(hours * 60))
    return minutes


def compute_travel_minutes(distance_km: float) -> tuple[int, int, int]:
    walking_minutes = _minutes_for_mode(distance_km, WALKING_SPEED_KMPH)
    driving_minutes = _minutes_for_mode(distance_km, DRIVING_SPEED_KMPH)
    fastest_minutes = min(walking_minutes, driving_minutes)
    return walking_minutes, driving_minutes, fastest_minutes
