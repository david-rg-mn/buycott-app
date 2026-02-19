from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from ..config import settings

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def is_open_now(hours_json: dict | None, timezone_name: str | None, now_utc: datetime | None = None) -> bool:
    if not hours_json:
        return True

    timezone = timezone_name or settings.default_timezone
    try:
        local_zone = ZoneInfo(timezone)
    except Exception:
        local_zone = ZoneInfo(settings.default_timezone)

    now = now_utc or datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
    local_now = now.astimezone(local_zone)

    day_key = DAY_KEYS[local_now.weekday()]
    windows = hours_json.get(day_key, [])
    if not windows:
        return False

    current_t = local_now.time()
    for start_raw, end_raw in windows:
        start = _parse_hhmm(start_raw)
        end = _parse_hhmm(end_raw)

        if start <= end:
            if start <= current_t <= end:
                return True
        else:
            if current_t >= start or current_t <= end:
                return True

    return False
