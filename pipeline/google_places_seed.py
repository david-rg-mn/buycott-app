#!/usr/bin/env python3
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, select

from common import get_session, utcnow

POWDERHORN_CENTER_LAT = 44.9485
POWDERHORN_CENTER_LNG = -93.2547
POWDERHORN_RADIUS_METERS = int(1.5 * 1609.344)

PLACES_API_BASE_URL = "https://places.googleapis.com/v1"
SEARCH_TEXT_ENDPOINT = "/places:searchText"
PLACE_DETAILS_ENDPOINT = "/places/{place_id}"
REQUEST_COST_USD = 0.017
MAX_SEARCH_PAGES = 3
SEARCH_QUERY = "businesses near Powderhorn Park, Minneapolis"

SEARCH_FIELD_MASK = "places.id,nextPageToken"
DETAILS_FIELD_MASK = (
    "id,displayName,formattedAddress,location,types,websiteUri,nationalPhoneNumber,regularOpeningHours"
)
PLACES_SOURCE_TYPE = "places_api"
WEEKDAY_KEYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]


class BudgetAbort(RuntimeError):
    pass


@dataclass
class RunStats:
    inserted: int = 0
    updated: int = 0
    skipped_fresh: int = 0
    skipped_missing_location: int = 0
    detail_failures: int = 0


class CostGuard:
    def __init__(self, max_run_cost_usd: float, max_monthly_cost_usd: float) -> None:
        self.max_run_cost_usd = max_run_cost_usd
        self.max_monthly_cost_usd = max_monthly_cost_usd
        self.request_count = 0
        self.rolling_30d_cost = 0.0

    @property
    def estimated_cost(self) -> float:
        return round(self.request_count * REQUEST_COST_USD, 6)

    def load_monthly_cost(self, session, GoogleApiUsageLog) -> None:
        cutoff = utcnow().replace(tzinfo=None) - timedelta(days=30)
        stmt = select(func.coalesce(func.sum(GoogleApiUsageLog.estimated_cost), 0.0)).where(
            GoogleApiUsageLog.timestamp >= cutoff
        )
        self.rolling_30d_cost = float(session.execute(stmt).scalar_one() or 0.0)
        if self.rolling_30d_cost >= self.max_monthly_cost_usd:
            raise BudgetAbort(
                f"Aborting: rolling 30-day Google API cost is ${self.rolling_30d_cost:.2f}, "
                f"limit is ${self.max_monthly_cost_usd:.2f}."
            )

    def ensure_request_budget(self) -> None:
        run_cost = self.request_count * REQUEST_COST_USD
        if run_cost >= self.max_run_cost_usd:
            raise BudgetAbort(
                f"Aborting: run cost reached ${run_cost:.3f}, limit is ${self.max_run_cost_usd:.2f}."
            )

    def record_request(self) -> None:
        self.request_count += 1


def _require_api_key() -> str:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is required")
    return api_key


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid {name} value: {raw_value}") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be > 0")
    return value


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid {name} value: {raw_value}") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be > 0")
    return value


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_stale(last_fetched: datetime | None, ttl_days: int) -> bool:
    if last_fetched is None:
        return True
    threshold = timedelta(days=ttl_days)
    return utcnow() - _as_utc(last_fetched) > threshold


def _extract_place_id(item: dict[str, Any]) -> str | None:
    place_id = item.get("id")
    if isinstance(place_id, str) and place_id.strip():
        return place_id.strip()

    resource_name = item.get("name")
    if isinstance(resource_name, str) and resource_name.startswith("places/"):
        return resource_name.split("/", maxsplit=1)[1].strip() or None
    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return str(value).strip() or None


def _coerce_display_name(payload: dict[str, Any]) -> str | None:
    display_name = payload.get("displayName")
    if isinstance(display_name, dict):
        return _coerce_text(display_name.get("text"))
    return _coerce_text(display_name)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def _normalize_types(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        item_text = _coerce_text(item)
        if item_text is None:
            continue
        normalized.append(item_text)
    return normalized


def _normalize_hours(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _google_hours_to_internal_windows(hours: dict[str, Any] | None) -> dict[str, list[list[str]]]:
    normalized: dict[str, list[list[str]]] = {
        "mon": [],
        "tue": [],
        "wed": [],
        "thu": [],
        "fri": [],
        "sat": [],
        "sun": [],
    }
    if hours is None:
        return normalized

    periods = hours.get("periods")
    if not isinstance(periods, list):
        return normalized

    def _fmt_hhmm(day_time: dict[str, Any], default: str) -> str:
        try:
            hour = int(day_time.get("hour", 0))
            minute = int(day_time.get("minute", 0))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                return default
            return f"{hour:02d}:{minute:02d}"
        except (TypeError, ValueError):
            return default

    def _append_window(day_index: int, start: str, end: str) -> None:
        day_key = WEEKDAY_KEYS[day_index]
        internal_key = "sun" if day_key == "sun" else day_key
        normalized[internal_key].append([start, end])

    for item in periods:
        if not isinstance(item, dict):
            continue
        open_info = item.get("open")
        close_info = item.get("close")
        if not isinstance(open_info, dict) or not isinstance(close_info, dict):
            continue

        try:
            open_day = int(open_info["day"])
            close_day = int(close_info["day"])
        except (KeyError, TypeError, ValueError):
            continue
        if open_day < 0 or open_day > 6 or close_day < 0 or close_day > 6:
            continue

        start_time = _fmt_hhmm(open_info, "00:00")
        end_time = _fmt_hhmm(close_info, "23:59")

        if open_day == close_day:
            _append_window(open_day, start_time, end_time)
            continue

        _append_window(open_day, start_time, "23:59")
        current_day = (open_day + 1) % 7
        while current_day != close_day:
            _append_window(current_day, "00:00", "23:59")
            current_day = (current_day + 1) % 7
        _append_window(close_day, "00:00", end_time)

    if all(not windows for windows in normalized.values()):
        return {}
    return normalized


def _build_text_content(
    name: str,
    formatted_address: str | None,
    types: list[str],
    hours: dict[str, Any] | None,
) -> str:
    parts: list[str] = [name]
    if formatted_address:
        parts.append(formatted_address)
    if types:
        parts.append("Types: " + ", ".join(types))

    weekday_descriptions = hours.get("weekdayDescriptions") if hours else None
    if isinstance(weekday_descriptions, list):
        readable_lines = [_coerce_text(line) for line in weekday_descriptions]
        cleaned = [line for line in readable_lines if line]
        if cleaned:
            parts.append("Hours: " + "; ".join(cleaned))
    return ". ".join(parts)


def _google_headers(api_key: str, field_mask: str) -> dict[str, str]:
    return {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask,
        "Content-Type": "application/json",
    }


def _request_json(
    client: httpx.Client,
    method: str,
    endpoint: str,
    headers: dict[str, str],
    guard: CostGuard,
    *,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    guard.ensure_request_budget()
    guard.record_request()
    response = client.request(method=method, url=endpoint, headers=headers, json=json)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected Google Places response payload")
    return payload


def _search_place_ids(client: httpx.Client, api_key: str, guard: CostGuard) -> list[str]:
    place_ids: list[str] = []
    seen_ids: set[str] = set()
    page_token: str | None = None

    for _ in range(MAX_SEARCH_PAGES):
        body: dict[str, Any] = {
            "textQuery": SEARCH_QUERY,
            "pageSize": 20,
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": POWDERHORN_CENTER_LAT,
                        "longitude": POWDERHORN_CENTER_LNG,
                    },
                    "radius": POWDERHORN_RADIUS_METERS,
                }
            },
        }
        if page_token:
            body["pageToken"] = page_token

        payload = _request_json(
            client=client,
            method="POST",
            endpoint=SEARCH_TEXT_ENDPOINT,
            headers=_google_headers(api_key, SEARCH_FIELD_MASK),
            guard=guard,
            json=body,
        )

        for place in payload.get("places", []):
            if not isinstance(place, dict):
                continue
            place_id = _extract_place_id(place)
            if place_id is None or place_id in seen_ids:
                continue
            seen_ids.add(place_id)
            place_ids.append(place_id)

        next_page = payload.get("nextPageToken")
        if not isinstance(next_page, str) or not next_page.strip():
            break
        page_token = next_page.strip()
        time.sleep(2.0)

    return place_ids


def _fetch_place_details(client: httpx.Client, api_key: str, guard: CostGuard, place_id: str) -> dict[str, Any]:
    return _request_json(
        client=client,
        method="GET",
        endpoint=PLACE_DETAILS_ENDPOINT.format(place_id=place_id),
        headers=_google_headers(api_key, DETAILS_FIELD_MASK),
        guard=guard,
    )


def _upsert_google_source(session, BusinessSource, business_id: int, place_id: str, snippet: str | None) -> None:
    source_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    stmt = select(BusinessSource).where(
        BusinessSource.business_id == business_id,
        BusinessSource.source_type == PLACES_SOURCE_TYPE,
        BusinessSource.source_url == source_url,
    )
    existing = session.execute(stmt).scalar_one_or_none()
    if existing is None:
        session.add(
            BusinessSource(
                business_id=business_id,
                source_type=PLACES_SOURCE_TYPE,
                source_url=source_url,
                snippet=snippet,
                last_fetched=utcnow(),
            )
        )
        return
    existing.snippet = snippet
    existing.last_fetched = utcnow()


def run() -> None:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    backend_path = root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.models import Business, BusinessSource, GoogleApiUsageLog

    api_key = _require_api_key()
    max_run_cost_usd = _env_float("MAX_RUN_COST_USD", 1.0)
    max_monthly_cost_usd = _env_float("MAX_MONTHLY_COST_USD", 5.0)
    ttl_days = _env_int("GOOGLE_DATA_TTL_DAYS", 30)

    session = get_session()
    guard = CostGuard(max_run_cost_usd=max_run_cost_usd, max_monthly_cost_usd=max_monthly_cost_usd)
    stats = RunStats()
    now_utc = utcnow()
    now_utc_naive = now_utc.replace(tzinfo=None)

    try:
        guard.load_monthly_cost(session, GoogleApiUsageLog)
        with httpx.Client(base_url=PLACES_API_BASE_URL, timeout=20.0) as client:
            place_ids = _search_place_ids(client, api_key, guard)
            for place_id in place_ids:
                existing = session.execute(select(Business).where(Business.google_place_id == place_id)).scalar_one_or_none()
                if existing is not None and not _is_stale(existing.google_last_fetched_at, ttl_days):
                    stats.skipped_fresh += 1
                    continue

                try:
                    details = _fetch_place_details(client, api_key, guard, place_id)
                except httpx.HTTPError:
                    stats.detail_failures += 1
                    continue

                display_name = _coerce_display_name(details) or f"Google Place {place_id}"
                formatted_address = _coerce_text(details.get("formattedAddress"))
                location = details.get("location") if isinstance(details.get("location"), dict) else {}
                lat = _coerce_float(location.get("latitude"))
                lng = _coerce_float(location.get("longitude"))

                if existing is not None:
                    lat = lat if lat is not None else existing.lat
                    lng = lng if lng is not None else existing.lng

                if lat is None or lng is None:
                    stats.skipped_missing_location += 1
                    continue

                types = _normalize_types(details.get("types"))
                website = _coerce_text(details.get("websiteUri"))
                phone = _coerce_text(details.get("nationalPhoneNumber"))
                hours = _normalize_hours(details.get("regularOpeningHours"))
                text_content = _build_text_content(display_name, formatted_address, types, hours)

                if existing is None:
                    business = Business(
                        name=display_name,
                        text_content=text_content,
                    )
                    session.add(business)
                    stats.inserted += 1
                else:
                    business = existing
                    stats.updated += 1

                business.name = display_name
                business.google_place_id = place_id
                business.formatted_address = formatted_address
                business.latitude = lat
                business.longitude = lng
                business.lat = lat
                business.lng = lng
                business.phone = phone
                business.website = website
                business.hours = hours
                business.hours_json = _google_hours_to_internal_windows(hours)
                business.types = types
                business.google_last_fetched_at = now_utc_naive
                business.google_source = "places_api"
                business.text_content = text_content
                business.last_updated = now_utc

                session.flush()
                _upsert_google_source(
                    session=session,
                    BusinessSource=BusinessSource,
                    business_id=business.id,
                    place_id=place_id,
                    snippet=formatted_address,
                )

        session.add(
            GoogleApiUsageLog(
                timestamp=now_utc_naive,
                requests_made=guard.request_count,
                estimated_cost=guard.estimated_cost,
            )
        )
        session.commit()
        print(
            "Google Places seed complete: "
            f"inserted={stats.inserted}, updated={stats.updated}, skipped_fresh={stats.skipped_fresh}, "
            f"missing_location={stats.skipped_missing_location}, detail_failures={stats.detail_failures}, "
            f"requests={guard.request_count}, estimated_cost=${guard.estimated_cost:.3f}"
        )
    except Exception:
        session.rollback()
        if guard.request_count > 0:
            try:
                session.add(
                    GoogleApiUsageLog(
                        timestamp=utcnow().replace(tzinfo=None),
                        requests_made=guard.request_count,
                        estimated_cost=guard.estimated_cost,
                    )
                )
                session.commit()
            except Exception:
                session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
