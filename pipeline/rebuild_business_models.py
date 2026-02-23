#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from common import get_session

ROOT = Path(__file__).resolve().parents[1]


def _inject_backend_path() -> None:
    backend_path = ROOT / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill Places-only business_model objects with fixed schema keys.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max businesses to process.",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only rebuild rows with missing/invalid business_model payloads.",
    )
    return parser.parse_args()


def _as_bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _existing_value(existing: dict[str, Any], *path: str) -> Any:
    current: Any = existing
    for step in path:
        if not isinstance(current, dict):
            return None
        if step not in current:
            return None
        current = current[step]
    return current


def _build_place_payload_from_business(business: Any, existing: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    if isinstance(business.primary_type, str) and business.primary_type.strip():
        payload["primaryType"] = business.primary_type.strip()

    if isinstance(business.types, list):
        payload["types"] = [item for item in business.types if isinstance(item, str)]

    existing_status = _existing_value(existing, "business_model", "operational", "business_status")
    if isinstance(existing_status, str) and existing_status.strip():
        payload["businessStatus"] = existing_status.strip()

    existing_psab = _existing_value(existing, "business_model", "storefront", "pure_service_area_business")
    if isinstance(existing_psab, bool):
        payload["pureServiceAreaBusiness"] = existing_psab

    for src_key, payload_key in {
        "delivery": "delivery",
        "takeout": "takeout",
        "dine_in": "dineIn",
        "curbside_pickup": "curbsidePickup",
    }.items():
        value = _existing_value(existing, "business_model", "fulfillment", src_key)
        if isinstance(value, bool):
            payload[payload_key] = value

    reservable = _existing_value(existing, "business_model", "booking", "reservable")
    if isinstance(reservable, bool):
        payload["reservable"] = reservable

    open_now = _existing_value(existing, "business_model", "operational", "open_now")
    if isinstance(open_now, bool):
        payload["currentOpeningHours"] = {"openNow": open_now}

    if isinstance(business.hours, dict) and business.hours:
        payload["regularOpeningHours"] = business.hours

    for src_key, payload_key in {
        "accessibility_options_present": "accessibilityOptions",
        "payment_options_present": "paymentOptions",
        "parking_options_present": "parkingOptions",
    }.items():
        value = _existing_value(existing, "business_model", "extras", src_key)
        bool_value = _as_bool_or_none(value)
        if bool_value is True:
            payload[payload_key] = {}

    return payload


def main() -> None:
    args = _parse_args()
    _inject_backend_path()

    from app.models import Business
    from app.services.business_model_service import (
        build_business_model_from_places,
        normalize_business_model_document,
    )

    session = get_session()
    now = datetime.now(timezone.utc)
    updated = 0

    try:
        stmt = select(Business).order_by(Business.id.asc())
        if args.limit is not None and args.limit > 0:
            stmt = stmt.limit(args.limit)

        rows = session.execute(stmt).scalars().all()
        for business in rows:
            existing_model = normalize_business_model_document(
                business.business_model if isinstance(business.business_model, dict) else None,
                field_mask="stored_backfill",
                computed_at=now,
            )

            if args.only_missing:
                schema_version = existing_model.get("schema_version")
                if schema_version == "1.0":
                    has_consumer_key = _existing_value(existing_model, "business_model", "consumer_facing") is not None
                    has_storefront_key = _existing_value(existing_model, "business_model", "storefront", "has_storefront") is not None
                    if has_consumer_key and has_storefront_key:
                        continue

            place_payload = _build_place_payload_from_business(business, existing_model)
            rebuilt = build_business_model_from_places(
                place_payload,
                field_mask="stored_backfill",
                computed_at=now,
            )

            business.business_model = rebuilt
            business.last_updated = now
            updated += 1

        session.commit()
        print(f"Business model backfill complete: updated={updated}, scanned={len(rows)}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
