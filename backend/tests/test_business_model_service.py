from __future__ import annotations

from app.services.business_model_service import (
    BusinessModelFilters,
    build_business_model_from_places,
    default_business_model_document,
    normalize_business_model_document,
    passes_business_model_filters,
)


def _bm(place: dict) -> dict:
    return build_business_model_from_places(place, field_mask="id,primaryType,types")


def test_default_business_model_has_fixed_keys() -> None:
    payload = default_business_model_document(field_mask="id")
    assert payload["schema_version"] == "1.0"
    bm = payload["business_model"]
    assert set(bm.keys()) == {
        "consumer_facing",
        "b2b_only",
        "appointment_required",
        "restricted_access",
        "storefront",
        "fulfillment",
        "booking",
        "operational",
        "extras",
        "provenance",
    }
    assert set(bm["storefront"].keys()) == {
        "pure_service_area_business",
        "service_area_only",
        "has_storefront",
    }
    assert set(bm["provenance"].keys()) == {
        "source",
        "field_mask_hash",
        "computed_at",
    }


def test_pure_service_area_business_mapping() -> None:
    payload = _bm({"primaryType": "restaurant", "pureServiceAreaBusiness": True})
    storefront = payload["business_model"]["storefront"]

    assert storefront["pure_service_area_business"] is True
    assert storefront["service_area_only"] is True
    assert storefront["has_storefront"] is False


def test_fulfillment_and_booking_fields_are_direct_mapped() -> None:
    payload = _bm(
        {
            "primaryType": "restaurant",
            "delivery": True,
            "takeout": False,
            "dineIn": True,
            "curbsidePickup": False,
            "reservable": True,
        }
    )
    fulfillment = payload["business_model"]["fulfillment"]
    booking = payload["business_model"]["booking"]

    assert fulfillment == {
        "dine_in": True,
        "takeout": False,
        "delivery": True,
        "curbside_pickup": False,
    }
    assert booking["reservable"] is True


def test_missing_fields_propagate_null_values() -> None:
    payload = _bm({"primaryType": "restaurant"})
    bm = payload["business_model"]

    assert bm["fulfillment"]["delivery"] is None
    assert bm["fulfillment"]["takeout"] is None
    assert bm["operational"]["open_now"] is None
    assert bm["extras"]["payment_options_present"] is None


def test_primary_type_allow_and_deny_behavior() -> None:
    allow_payload = _bm({"primaryType": "restaurant"})
    liquor_payload = _bm({"primaryType": "liquor_store"})
    repair_payload = _bm({"primaryType": "car_repair"})
    deny_payload = _bm({"primaryType": "corporate_office"})
    supplier_payload = _bm({"primaryType": "supplier"})
    unknown_payload = _bm({"primaryType": "unknown_custom_type"})

    assert allow_payload["business_model"]["consumer_facing"] is True
    assert liquor_payload["business_model"]["consumer_facing"] is True
    assert repair_payload["business_model"]["consumer_facing"] is True
    assert deny_payload["business_model"]["consumer_facing"] is False
    assert supplier_payload["business_model"]["consumer_facing"] is False
    assert supplier_payload["business_model"]["b2b_only"] is True
    assert unknown_payload["business_model"]["consumer_facing"] is None


def test_consumer_facing_falls_back_to_types_when_primary_missing_or_unknown() -> None:
    missing_primary = _bm({"types": ["mexican_restaurant", "restaurant"]})
    unknown_primary = _bm({"primaryType": "unknown_custom_type", "types": ["grocery_store"]})

    assert missing_primary["business_model"]["consumer_facing"] is True
    assert unknown_primary["business_model"]["consumer_facing"] is True


def test_consumer_facing_type_conflict_remains_null() -> None:
    payload = _bm({"types": ["grocery_store", "warehouse"]})
    assert payload["business_model"]["consumer_facing"] is None


def test_strict_appointment_and_restricted_types_only() -> None:
    dentist = _bm({"primaryType": "dentist"})
    military = _bm({"primaryType": "military_base"})
    restaurant = _bm({"primaryType": "restaurant"})

    assert dentist["business_model"]["appointment_required"] is True
    assert military["business_model"]["restricted_access"] is True
    assert restaurant["business_model"]["appointment_required"] is None
    assert restaurant["business_model"]["restricted_access"] is None


def test_open_now_and_regular_hours_derivation() -> None:
    payload = _bm(
        {
            "primaryType": "restaurant",
            "businessStatus": "OPERATIONAL",
            "currentOpeningHours": {"openNow": True},
            "regularOpeningHours": {},
        }
    )
    operational = payload["business_model"]["operational"]

    assert operational["business_status"] == "OPERATIONAL"
    assert operational["open_now"] is True
    assert operational["has_regular_opening_hours"] is True


def test_extras_presence_flags_follow_field_presence() -> None:
    payload = _bm(
        {
            "primaryType": "restaurant",
            "accessibilityOptions": None,
            "paymentOptions": {},
            "parkingOptions": {"garage": True},
        }
    )
    extras = payload["business_model"]["extras"]

    assert extras["accessibility_options_present"] is True
    assert extras["payment_options_present"] is True
    assert extras["parking_options_present"] is True


def test_query_time_filter_evaluation() -> None:
    payload = _bm(
        {
            "primaryType": "restaurant",
            "pureServiceAreaBusiness": False,
            "delivery": True,
            "takeout": True,
            "dineIn": False,
            "curbsidePickup": True,
            "currentOpeningHours": {"openNow": True},
        }
    )

    passes, reasons = passes_business_model_filters(
        payload,
        BusinessModelFilters(
            consumer_facing_only=True,
            include_service_area_businesses=False,
            require_delivery=True,
            require_takeout=True,
            require_dine_in=False,
            require_curbside_pickup=True,
            open_now=True,
        ),
    )
    assert passes
    assert reasons == []

    service_area_payload = _bm({"primaryType": "restaurant", "pureServiceAreaBusiness": True})
    passes, reasons = passes_business_model_filters(
        service_area_payload,
        BusinessModelFilters(consumer_facing_only=True, include_service_area_businesses=False),
    )
    assert not passes
    assert "service_area_only" in reasons


def test_normalize_business_model_document_fills_missing_shape() -> None:
    partial = {
        "schema_version": "0.1",
        "business_model": {
            "consumer_facing": True,
            "storefront": {"service_area_only": False},
        },
    }
    normalized = normalize_business_model_document(partial)

    assert normalized["schema_version"] == "1.0"
    assert normalized["business_model"]["consumer_facing"] is True
    assert normalized["business_model"]["storefront"]["service_area_only"] is False
    assert "booking" in normalized["business_model"]
