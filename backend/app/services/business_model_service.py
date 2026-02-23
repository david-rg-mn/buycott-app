from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class BusinessModelTypeTables:
    version: str
    consumer_facing_allowlist: frozenset[str]
    non_consumer_denylist: frozenset[str]
    b2b_strict_list: frozenset[str]
    strict_appointment_types: frozenset[str]
    strict_restricted_types: frozenset[str]


@dataclass(frozen=True, slots=True)
class BusinessModelFilters:
    consumer_facing_only: bool = True
    include_service_area_businesses: bool = False
    require_delivery: bool = False
    require_takeout: bool = False
    require_dine_in: bool = False
    require_curbside_pickup: bool = False
    open_now: bool = False


def _root_path() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_type_tables() -> BusinessModelTypeTables:
    table_path = _root_path() / "data" / "raw" / "business_model" / "type_tables.v1.json"
    payload = json.loads(table_path.read_text(encoding="utf-8"))

    def _as_set(key: str) -> frozenset[str]:
        raw = payload.get(key, [])
        if not isinstance(raw, list):
            return frozenset()
        cleaned = {
            str(item).strip().lower()
            for item in raw
            if isinstance(item, str) and str(item).strip()
        }
        return frozenset(cleaned)

    return BusinessModelTypeTables(
        version=str(payload.get("version") or "unknown"),
        consumer_facing_allowlist=_as_set("consumer_facing_allowlist"),
        non_consumer_denylist=_as_set("non_consumer_denylist"),
        b2b_strict_list=_as_set("b2b_strict_list"),
        strict_appointment_types=_as_set("strict_appointment_types"),
        strict_restricted_types=_as_set("strict_restricted_types"),
    )


def _as_bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _as_text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _nested_get(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = mapping
    for step in path:
        if not isinstance(current, Mapping):
            return None
        if step not in current:
            return None
        current = current[step]
    return current


def _nested_set(mapping: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = mapping
    for step in path[:-1]:
        child = current.get(step)
        if not isinstance(child, dict):
            child = {}
            current[step] = child
        current = child
    current[path[-1]] = value


def _field_mask_hash(field_mask: str | None) -> str | None:
    if field_mask is None:
        return None
    normalized = field_mask.strip()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def default_business_model_document(
    *,
    field_mask: str | None = None,
    computed_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = computed_at.isoformat() if computed_at is not None else None
    return {
        "schema_version": "1.0",
        "business_model": {
            "consumer_facing": None,
            "b2b_only": None,
            "appointment_required": None,
            "restricted_access": None,
            "storefront": {
                "pure_service_area_business": None,
                "service_area_only": None,
                "has_storefront": None,
            },
            "fulfillment": {
                "dine_in": None,
                "takeout": None,
                "delivery": None,
                "curbside_pickup": None,
            },
            "booking": {
                "reservable": None,
            },
            "operational": {
                "business_status": None,
                "open_now": None,
                "has_regular_opening_hours": None,
            },
            "extras": {
                "accessibility_options_present": None,
                "payment_options_present": None,
                "parking_options_present": None,
            },
            "provenance": {
                "source": "google_places_api_new",
                "field_mask_hash": _field_mask_hash(field_mask),
                "computed_at": timestamp,
            },
        },
    }


def normalize_business_model_document(
    payload: Mapping[str, Any] | None,
    *,
    field_mask: str | None = None,
    computed_at: datetime | None = None,
) -> dict[str, Any]:
    base = default_business_model_document(field_mask=field_mask, computed_at=computed_at)
    if not isinstance(payload, Mapping):
        return base

    source_paths = [
        ("schema_version",),
        ("business_model", "consumer_facing"),
        ("business_model", "b2b_only"),
        ("business_model", "appointment_required"),
        ("business_model", "restricted_access"),
        ("business_model", "storefront", "pure_service_area_business"),
        ("business_model", "storefront", "service_area_only"),
        ("business_model", "storefront", "has_storefront"),
        ("business_model", "fulfillment", "dine_in"),
        ("business_model", "fulfillment", "takeout"),
        ("business_model", "fulfillment", "delivery"),
        ("business_model", "fulfillment", "curbside_pickup"),
        ("business_model", "booking", "reservable"),
        ("business_model", "operational", "business_status"),
        ("business_model", "operational", "open_now"),
        ("business_model", "operational", "has_regular_opening_hours"),
        ("business_model", "extras", "accessibility_options_present"),
        ("business_model", "extras", "payment_options_present"),
        ("business_model", "extras", "parking_options_present"),
        ("business_model", "provenance", "source"),
        ("business_model", "provenance", "field_mask_hash"),
        ("business_model", "provenance", "computed_at"),
    ]

    output = copy.deepcopy(base)
    for path in source_paths:
        value = _nested_get(payload, path)
        if value is None:
            continue
        _nested_set(output, path, value)

    if _nested_get(output, ("schema_version",)) != "1.0":
        _nested_set(output, ("schema_version",), "1.0")
    return output


def build_business_model_from_places(
    place: Mapping[str, Any],
    *,
    field_mask: str | None,
    computed_at: datetime | None = None,
) -> dict[str, Any]:
    tables = load_type_tables()
    model_doc = default_business_model_document(field_mask=field_mask, computed_at=computed_at)
    model = model_doc["business_model"]

    primary_type = _as_text_or_none(place.get("primaryType"))
    primary_key = primary_type.lower() if primary_type else None
    raw_types = place.get("types")
    type_keys: set[str] = set()
    if isinstance(raw_types, list):
        for raw in raw_types:
            type_text = _as_text_or_none(raw)
            if type_text:
                type_keys.add(type_text.lower())

    pure_service_area_business = _as_bool_or_none(place.get("pureServiceAreaBusiness"))
    model["storefront"]["pure_service_area_business"] = pure_service_area_business
    if pure_service_area_business is True:
        model["storefront"]["service_area_only"] = True
        model["storefront"]["has_storefront"] = False
    elif pure_service_area_business is False:
        model["storefront"]["service_area_only"] = False
        model["storefront"]["has_storefront"] = True

    model["fulfillment"]["delivery"] = _as_bool_or_none(place.get("delivery"))
    model["fulfillment"]["takeout"] = _as_bool_or_none(place.get("takeout"))
    model["fulfillment"]["dine_in"] = _as_bool_or_none(place.get("dineIn"))
    model["fulfillment"]["curbside_pickup"] = _as_bool_or_none(place.get("curbsidePickup"))

    model["booking"]["reservable"] = _as_bool_or_none(place.get("reservable"))

    model["operational"]["business_status"] = _as_text_or_none(place.get("businessStatus"))

    current_hours = place.get("currentOpeningHours")
    open_now = None
    if isinstance(current_hours, Mapping):
        open_now = _as_bool_or_none(current_hours.get("openNow"))
    model["operational"]["open_now"] = open_now

    if "regularOpeningHours" in place:
        model["operational"]["has_regular_opening_hours"] = True

    if primary_key and primary_key in tables.consumer_facing_allowlist:
        model["consumer_facing"] = True
    elif primary_key and primary_key in tables.non_consumer_denylist:
        model["consumer_facing"] = False
    else:
        has_allow_type = bool(type_keys.intersection(tables.consumer_facing_allowlist))
        has_deny_type = bool(type_keys.intersection(tables.non_consumer_denylist))
        if has_allow_type and not has_deny_type:
            model["consumer_facing"] = True
        elif has_deny_type and not has_allow_type:
            model["consumer_facing"] = False

    if primary_key and primary_key in tables.b2b_strict_list:
        model["b2b_only"] = True
    elif not primary_key and type_keys.intersection(tables.b2b_strict_list):
        model["b2b_only"] = True

    if primary_key and primary_key in tables.strict_appointment_types:
        model["appointment_required"] = True

    if primary_key and primary_key in tables.strict_restricted_types:
        model["restricted_access"] = True

    if "accessibilityOptions" in place:
        model["extras"]["accessibility_options_present"] = True
    if "paymentOptions" in place:
        model["extras"]["payment_options_present"] = True
    if "parkingOptions" in place:
        model["extras"]["parking_options_present"] = True
    return model_doc


def business_model_value(document: Mapping[str, Any] | None, *path: str) -> Any:
    if not isinstance(document, Mapping):
        return None
    return _nested_get(document, tuple(path))


def passes_business_model_filters(
    document: Mapping[str, Any] | None,
    filters: BusinessModelFilters,
) -> tuple[bool, list[str]]:
    normalized = normalize_business_model_document(document)
    bm = normalized["business_model"]
    reasons: list[str] = []

    if filters.consumer_facing_only and bm.get("consumer_facing") is not True:
        reasons.append("consumer_facing_only")

    service_area_only = bm.get("storefront", {}).get("service_area_only")
    if not filters.include_service_area_businesses and service_area_only is True:
        reasons.append("service_area_only")

    if filters.require_delivery and bm.get("fulfillment", {}).get("delivery") is not True:
        reasons.append("require_delivery")
    if filters.require_takeout and bm.get("fulfillment", {}).get("takeout") is not True:
        reasons.append("require_takeout")
    if filters.require_dine_in and bm.get("fulfillment", {}).get("dine_in") is not True:
        reasons.append("require_dine_in")
    if filters.require_curbside_pickup and bm.get("fulfillment", {}).get("curbside_pickup") is not True:
        reasons.append("require_curbside_pickup")

    if filters.open_now and bm.get("operational", {}).get("open_now") is not True:
        reasons.append("open_now")

    return len(reasons) == 0, reasons
