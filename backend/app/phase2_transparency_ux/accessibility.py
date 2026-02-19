from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time
from typing import Protocol
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.phase1_semantic_pipeline.embeddings import km_to_minutes


class HourLike(Protocol):
    day_of_week: int
    opens_at: time
    closes_at: time
    timezone: str


@dataclass(frozen=True)
class TravelMetrics:
    distance_km: float
    walking_minutes: int
    driving_minutes: int
    minutes_away: int


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def compute_travel_metrics(user_lat: float, user_lng: float, business_lat: float, business_lng: float) -> TravelMetrics:
    settings = get_settings()
    distance = haversine_km(user_lat, user_lng, business_lat, business_lng)
    walking = km_to_minutes(distance, settings.walking_kmh_default)
    driving = km_to_minutes(distance, settings.driving_kmh_default)
    minutes_away = min(walking, driving)
    return TravelMetrics(
        distance_km=distance,
        walking_minutes=walking,
        driving_minutes=driving,
        minutes_away=minutes_away,
    )


def is_open_now(hours: list[HourLike], now_utc: datetime | None = None) -> bool:
    if not hours:
        return False

    now_utc = now_utc or datetime.now(tz=ZoneInfo("UTC"))

    for row in hours:
        tz = ZoneInfo(row.timezone)
        local_now = now_utc.astimezone(tz)

        if local_now.weekday() != row.day_of_week:
            continue

        open_time = row.opens_at
        close_time = row.closes_at
        now_t = local_now.time()

        if open_time <= close_time:
            if open_time <= now_t <= close_time:
                return True
        else:
            # Overnight span, e.g. 22:00-02:00
            if now_t >= open_time or now_t <= close_time:
                return True

    return False
