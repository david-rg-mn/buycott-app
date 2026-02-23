from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Business, BusinessCapability, BusinessSource, CapabilityProfile, MenuItem
from .business_model_service import (
    BusinessModelFilters,
    normalize_business_model_document,
    passes_business_model_filters,
)
from ..schemas import (
    BusinessSearchResult,
    CapabilitiesResponse,
    CapabilityView,
    EvidenceExplanationResponse,
    SearchResponse,
    SourceView,
)
from ..telemetry import get_current_trace, instrument_stage
from .distance_service import compute_travel_minutes, haversine_km
from .embedding_service import get_embedding_service
from .ontology_service import ontology_service
from .time_service import is_open_now

logger = logging.getLogger(__name__)

_MENU_INGREDIENT_TERMS: tuple[str, ...] = (
    "carrot",
    "jalapeno",
    "avocado",
    "beans",
    "rice",
    "cheese",
    "sour cream",
    "lettuce",
    "tomato",
    "onion",
    "cilantro",
    "lime",
    "guacamole",
    "salsa",
    "tortilla",
    "shrimp",
    "chicken",
    "beef",
    "pork",
    "fish",
)
_MENU_INGREDIENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (
        term,
        re.compile(rf"\b{re.escape(term)}(?:es|s)?\b", re.IGNORECASE),
    )
    for term in _MENU_INGREDIENT_TERMS
)


@dataclass
class SearchParams:
    query: str
    lat: float
    lng: float
    include_chains: bool = False
    open_now: bool = False
    walking_distance: bool = False
    consumer_facing_only: bool = True
    include_service_area_businesses: bool = False
    require_delivery: bool = False
    require_takeout: bool = False
    require_dine_in: bool = False
    require_curbside_pickup: bool = False
    walking_threshold_minutes: int = settings.walking_threshold_minutes
    limit: int = settings.search_result_limit


@dataclass
class Candidate:
    business: Business
    similarity: float
    matched_terms: set[str]


def _clamp_score(raw_similarity: float) -> int:
    scaled = int(round(raw_similarity * 100))
    return max(0, min(100, scaled))


def _proximity_score(distance_km: float) -> float:
    # 1.0 at the user's location, decays smoothly with distance.
    return 1.0 / (1.0 + max(0.0, distance_km) / 5.0)


def _ranking_score(*, similarity: float, distance_km: float, capability_confidence: float) -> float:
    proximity = _proximity_score(distance_km)
    cap_conf = max(0.0, min(1.0, capability_confidence))
    return (0.84 * max(0.0, similarity)) + (0.12 * proximity) + (0.04 * cap_conf)


def _extract_menu_description_terms(description: str | None) -> list[str]:
    if not isinstance(description, str):
        return []
    folded = (
        unicodedata.normalize("NFKD", description)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    matches: list[str] = []
    for term, pattern in _MENU_INGREDIENT_PATTERNS:
        if pattern.search(folded):
            matches.append(term)
    return matches


def _fetch_sources(db: Session, business_ids: list[int]) -> dict[int, list[BusinessSource]]:
    if not business_ids:
        return {}
    stmt = select(BusinessSource).where(BusinessSource.business_id.in_(business_ids))
    rows = db.execute(stmt).scalars().all()
    grouped: dict[int, list[BusinessSource]] = {}
    for row in rows:
        grouped.setdefault(row.business_id, []).append(row)
    return grouped


def _fetch_capabilities(db: Session, business_ids: list[int]) -> dict[int, list[BusinessCapability]]:
    if not business_ids:
        return {}

    stmt = (
        select(BusinessCapability)
        .where(BusinessCapability.business_id.in_(business_ids))
        .order_by(BusinessCapability.business_id.asc(), BusinessCapability.confidence_score.desc())
    )
    rows = db.execute(stmt).scalars().all()
    grouped: dict[int, list[BusinessCapability]] = {}
    for row in rows:
        grouped.setdefault(row.business_id, []).append(row)
    return grouped


class SearchService:
    def __init__(self) -> None:
        self.embedding_service = get_embedding_service()

    @staticmethod
    def _filters_payload(params: SearchParams) -> dict[str, bool | int]:
        return {
            "include_chains": params.include_chains,
            "open_now": params.open_now,
            "walking_distance": params.walking_distance,
            "consumer_facing_only": params.consumer_facing_only,
            "include_service_area_businesses": params.include_service_area_businesses,
            "require_delivery": params.require_delivery,
            "require_takeout": params.require_takeout,
            "require_dine_in": params.require_dine_in,
            "require_curbside_pickup": params.require_curbside_pickup,
            "walking_threshold_minutes": params.walking_threshold_minutes,
        }

    @staticmethod
    def _current_request_id() -> str | None:
        trace = get_current_trace()
        if trace is None:
            return None
        return str(trace.request_id)

    @staticmethod
    def _record_trace_query(query_text: str) -> None:
        trace = get_current_trace()
        if trace is None:
            return
        trace.mark_query(query_text)

    @staticmethod
    def _record_trace_results(result_count: int, top_similarity_score: float | None) -> None:
        trace = get_current_trace()
        if trace is None:
            return
        trace.set_result_summary(result_count, top_similarity_score)

    def _empty_response(
        self,
        query: str,
        expansion_chain: list[str],
        related_items: list[str],
        params: SearchParams,
    ) -> SearchResponse:
        return SearchResponse(
            query=query,
            expansion_chain=expansion_chain,
            related_items=related_items,
            local_only=not params.include_chains,
            filters=self._filters_payload(params),
            results=[],
            request_id=self._current_request_id(),
        )

    @instrument_stage("expansion")
    def _expand_query(self, db: Session, query: str) -> list[str]:
        return ontology_service.expand_query(db, query)

    @instrument_stage("expansion")
    def _related_items(self, db: Session, query: str) -> list[str]:
        return ontology_service.related_items(db, query)

    @instrument_stage("embedding")
    def _encode_terms(self, query_terms: list[str]) -> list[list[float]]:
        return self.embedding_service.encode_many(query_terms)

    @instrument_stage("db")
    def _collect_candidates(
        self,
        db: Session,
        params: SearchParams,
        query_terms: list[str],
        vectors: list[list[float]],
    ) -> dict[int, Candidate]:
        candidate_map: dict[int, Candidate] = {}

        for idx, vector in enumerate(vectors):
            search_term = query_terms[idx]
            distance_expr = Business.embedding.cosine_distance(vector)
            similarity_expr = (1 - distance_expr).label("similarity")

            stmt = select(Business, similarity_expr).where(Business.embedding.is_not(None))
            if not params.include_chains:
                stmt = stmt.where(Business.is_chain.is_(False))
            stmt = stmt.order_by(distance_expr.asc()).limit(settings.top_k_per_vector)

            for business, similarity in db.execute(stmt).all():
                if similarity is None:
                    continue
                similarity_float = float(similarity)
                existing = candidate_map.get(business.id)
                if existing is None:
                    candidate_map[business.id] = Candidate(
                        business=business,
                        similarity=similarity_float,
                        matched_terms={search_term},
                    )
                else:
                    existing.matched_terms.add(search_term)
                    if similarity_float > existing.similarity:
                        existing.similarity = similarity_float

        return candidate_map

    @instrument_stage("db")
    def _fetch_capabilities_map(
        self,
        db: Session,
        business_ids: list[int],
    ) -> dict[int, list[BusinessCapability]]:
        return _fetch_capabilities(db, business_ids)

    @instrument_stage("db")
    def _fetch_sources_map(
        self,
        db: Session,
        business_ids: list[int],
    ) -> dict[int, list[BusinessSource]]:
        return _fetch_sources(db, business_ids)

    @staticmethod
    def _to_business_model_filters(params: SearchParams) -> BusinessModelFilters:
        return BusinessModelFilters(
            consumer_facing_only=params.consumer_facing_only,
            include_service_area_businesses=params.include_service_area_businesses,
            require_delivery=params.require_delivery,
            require_takeout=params.require_takeout,
            require_dine_in=params.require_dine_in,
            require_curbside_pickup=params.require_curbside_pickup,
            open_now=False,
        )

    @staticmethod
    def _places_open_now(business_model: dict) -> bool | None:
        value = (
            business_model.get("business_model", {})
            .get("operational", {})
            .get("open_now")
        )
        if isinstance(value, bool):
            return value
        return None

    @instrument_stage("ranking")
    def _rank_candidates(
        self,
        candidate_map: dict[int, Candidate],
        capabilities_map: dict[int, list[BusinessCapability]],
        params: SearchParams,
        request_id: str | None,
    ) -> tuple[list[BusinessSearchResult], float]:
        scored_rows: list[tuple[float, BusinessSearchResult]] = []
        top_similarity = 0.0
        filtered_by_business_model = 0
        filtered_by_consumer_facing = 0
        filtered_by_open_now = 0
        filtered_by_distance = 0

        business_model_filters = self._to_business_model_filters(params)
        for candidate in candidate_map.values():
            if candidate.similarity < settings.min_similarity:
                continue

            business = candidate.business
            distance_km = haversine_km(params.lat, params.lng, business.lat, business.lng)
            if distance_km > settings.max_search_distance_km:
                filtered_by_distance += 1
                continue
            walking_minutes, driving_minutes, fastest_minutes = compute_travel_minutes(distance_km)

            if params.walking_distance and walking_minutes > params.walking_threshold_minutes:
                continue

            business_model = normalize_business_model_document(
                business.business_model if isinstance(business.business_model, dict) else None
            )
            passes_filters, reasons = passes_business_model_filters(
                business_model,
                business_model_filters,
            )
            if not passes_filters:
                filtered_by_business_model += 1
                if "consumer_facing_only" in reasons:
                    filtered_by_consumer_facing += 1
                continue

            places_open_now = self._places_open_now(business_model)
            open_flag = places_open_now if places_open_now is not None else is_open_now(business.hours_json, business.timezone)
            if params.open_now and places_open_now is not True:
                filtered_by_open_now += 1
                continue

            raw_types = business.types if isinstance(business.types, list) else []
            place_types = [item for item in raw_types if isinstance(item, str)]
            hours_payload = business.hours if isinstance(business.hours, dict) else None

            badges: list[str] = []
            if not business.is_chain:
                badges.append("Independent")

            caps = capabilities_map.get(business.id, [])
            top_capability_confidence = max((float(cap.confidence_score) for cap in caps), default=0.0)
            if business.specialty_score >= 0.72 or (caps and caps[0].confidence_score >= 0.82):
                badges.append("Specialist")

            top_similarity = max(top_similarity, candidate.similarity)
            row = BusinessSearchResult(
                    id=business.id,
                    name=business.name,
                    lat=business.lat,
                    lng=business.lng,
                    distance_km=round(distance_km, 2),
                    minutes_away=fastest_minutes,
                    driving_minutes=driving_minutes,
                    walking_minutes=walking_minutes,
                    evidence_score=_clamp_score(candidate.similarity),
                    is_chain=business.is_chain,
                    chain_name=business.chain_name,
                    formatted_address=business.formatted_address,
                    phone=business.phone,
                    website=business.website,
                    hours=hours_payload,
                    types=place_types,
                    open_now=open_flag,
                    badges=badges,
                    matched_terms=sorted(candidate.matched_terms),
                    last_updated=business.last_updated,
                    request_id=request_id,
            )
            rank_score = _ranking_score(
                similarity=candidate.similarity,
                distance_km=distance_km,
                capability_confidence=top_capability_confidence,
            )
            scored_rows.append((rank_score, row))

        scored_rows.sort(key=lambda item: (-item[0], item[1].distance_km, item[1].name.lower()))
        result_rows = [row for _score, row in scored_rows]
        if candidate_map:
            consumer_filter_rate = round((filtered_by_consumer_facing / len(candidate_map)) * 100.0, 2)
            logger.info(
                "business_model_filtering: candidates=%s kept=%s filtered_business_model=%s "
                "filtered_consumer_facing=%s filtered_consumer_facing_pct=%s filtered_open_now=%s filtered_distance=%s",
                len(candidate_map),
                len(result_rows),
                filtered_by_business_model,
                filtered_by_consumer_facing,
                consumer_filter_rate,
                filtered_by_open_now,
                filtered_by_distance,
            )
        return result_rows, top_similarity

    def search(self, db: Session, params: SearchParams) -> SearchResponse:
        clean_query = params.query.strip()
        if not clean_query:
            return self._empty_response(
                query=params.query,
                expansion_chain=[],
                related_items=[],
                params=params,
            )

        self._record_trace_query(clean_query)
        request_id = self._current_request_id()

        expansion_chain = self._expand_query(db, clean_query)
        query_terms = [clean_query]
        seen_terms = {clean_query.lower()}
        for term in expansion_chain:
            lowered = term.lower()
            if lowered not in seen_terms:
                seen_terms.add(lowered)
                query_terms.append(term)

        vectors = self._encode_terms(query_terms)
        candidate_map = self._collect_candidates(db, params, query_terms, vectors)
        related_items = self._related_items(db, clean_query)

        if not candidate_map:
            empty_ranked_rows, top_similarity = self._rank_candidates({}, {}, params, request_id)
            self._record_trace_results(len(empty_ranked_rows), top_similarity)
            return SearchResponse(
                query=clean_query,
                expansion_chain=expansion_chain,
                related_items=related_items,
                local_only=not params.include_chains,
                filters=self._filters_payload(params),
                results=empty_ranked_rows,
                request_id=request_id,
            )

        business_ids = list(candidate_map.keys())
        capabilities_map = self._fetch_capabilities_map(db, business_ids)
        _ = self._fetch_sources_map(db, business_ids)
        result_rows, top_similarity = self._rank_candidates(candidate_map, capabilities_map, params, request_id)
        limited_results = result_rows[: params.limit]
        self._record_trace_results(len(limited_results), top_similarity if limited_results else 0.0)

        return SearchResponse(
            query=clean_query,
            expansion_chain=expansion_chain,
            related_items=related_items,
            local_only=not params.include_chains,
            filters=self._filters_payload(params),
            results=limited_results,
            request_id=request_id,
        )

    def list_businesses(self, db: Session, params: SearchParams) -> SearchResponse:
        request_id = self._current_request_id()

        stmt = select(Business)
        if not params.include_chains:
            stmt = stmt.where(Business.is_chain.is_(False))
        businesses = db.execute(stmt).scalars().all()

        business_ids = [business.id for business in businesses]
        capabilities_map = self._fetch_capabilities_map(db, business_ids)
        _ = self._fetch_sources_map(db, business_ids)
        business_model_filters = self._to_business_model_filters(params)

        result_rows: list[BusinessSearchResult] = []
        for business in businesses:
            distance_km = haversine_km(params.lat, params.lng, business.lat, business.lng)
            if distance_km > settings.max_search_distance_km:
                continue
            walking_minutes, driving_minutes, fastest_minutes = compute_travel_minutes(distance_km)

            if params.walking_distance and walking_minutes > params.walking_threshold_minutes:
                continue

            business_model = normalize_business_model_document(
                business.business_model if isinstance(business.business_model, dict) else None
            )
            passes_filters, _reasons = passes_business_model_filters(
                business_model,
                business_model_filters,
            )
            if not passes_filters:
                continue

            places_open_now = self._places_open_now(business_model)
            open_flag = places_open_now if places_open_now is not None else is_open_now(business.hours_json, business.timezone)
            if params.open_now and places_open_now is not True:
                continue

            raw_types = business.types if isinstance(business.types, list) else []
            place_types = [item for item in raw_types if isinstance(item, str)]
            hours_payload = business.hours if isinstance(business.hours, dict) else None

            caps = capabilities_map.get(business.id, [])
            top_capability_confidence = max((cap.confidence_score for cap in caps), default=0.0)
            evidence_score = _clamp_score(max(float(business.specialty_score), float(top_capability_confidence)))

            badges: list[str] = []
            if not business.is_chain:
                badges.append("Independent")
            if business.specialty_score >= 0.72 or (caps and caps[0].confidence_score >= 0.82):
                badges.append("Specialist")

            result_rows.append(
                BusinessSearchResult(
                    id=business.id,
                    name=business.name,
                    lat=business.lat,
                    lng=business.lng,
                    distance_km=round(distance_km, 2),
                    minutes_away=fastest_minutes,
                    driving_minutes=driving_minutes,
                    walking_minutes=walking_minutes,
                    evidence_score=evidence_score,
                    is_chain=business.is_chain,
                    chain_name=business.chain_name,
                    formatted_address=business.formatted_address,
                    phone=business.phone,
                    website=business.website,
                    hours=hours_payload,
                    types=place_types,
                    open_now=open_flag,
                    badges=badges,
                    matched_terms=[],
                    last_updated=business.last_updated,
                    request_id=request_id,
                )
            )

        result_rows.sort(key=lambda item: (item.distance_km, item.name.lower()))
        limited_results = result_rows[: params.limit]
        self._record_trace_results(len(limited_results), None)

        return SearchResponse(
            query="all businesses",
            expansion_chain=[],
            related_items=[],
            local_only=not params.include_chains,
            filters=self._filters_payload(params),
            results=limited_results,
            request_id=request_id,
        )

    def business_capabilities(self, db: Session, business_id: int, limit: int = 8) -> CapabilitiesResponse:
        cap_limit = max(1, int(limit))
        response_terms: list[CapabilityView] = []

        def _clean_term(raw: str) -> str:
            text = " ".join(raw.strip().split())
            if not text:
                return ""
            words = text.split()
            if len(words) >= 4:
                max_window = min(6, len(words) // 2)
                for window in range(max_window, 0, -1):
                    if words[:window] == words[window : 2 * window]:
                        collapsed = " ".join(words[window:]).strip()
                        if collapsed:
                            text = collapsed
                            break
            return text

        def _append_term(*, term: str, confidence: float, source_reference: str) -> None:
            cleaned = _clean_term(term)
            if not cleaned:
                return
            cleaned_norm = cleaned.lower()
            if len(response_terms) >= cap_limit:
                return
            for idx, existing in enumerate(response_terms):
                existing_norm = existing.ontology_term.lower()
                if existing_norm == cleaned_norm:
                    return
                if existing_norm.endswith(f" {cleaned_norm}") and len(existing_norm) >= len(cleaned_norm) + 5:
                    response_terms[idx] = CapabilityView(
                        ontology_term=cleaned,
                        confidence_score=round(float(confidence), 3),
                        source_reference=source_reference,
                    )
                    return
                if cleaned_norm.endswith(f" {existing_norm}") and len(cleaned_norm) >= len(existing_norm) + 5:
                    return
            response_terms.append(
                CapabilityView(
                    ontology_term=cleaned,
                    confidence_score=round(float(confidence), 3),
                    source_reference=source_reference,
                )
            )

        def _collect_menu_item_names(rows: list[MenuItem]) -> list[str]:
            names: list[str] = []
            seen: set[str] = set()
            for row in rows:
                if not isinstance(row.item_name, str):
                    continue
                cleaned = _clean_term(row.item_name)
                if not cleaned:
                    continue
                normalized = cleaned.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                names.append(cleaned)
            return names

        profile_stmt = (
            select(CapabilityProfile)
            .where(CapabilityProfile.business_id == business_id)
            .order_by(CapabilityProfile.confidence_score.desc(), CapabilityProfile.id.asc())
        )
        profiles = db.execute(profile_stmt).scalars().all()
        reserve_menu_slots = min(10, max(2, cap_limit // 3))
        profile_budget = max(0, cap_limit - reserve_menu_slots)
        for profile in profiles:
            items = profile.canonical_items if isinstance(profile.canonical_items, list) else []
            for raw_term in items:
                if not isinstance(raw_term, str):
                    continue
                _append_term(
                    term=raw_term,
                    confidence=float(profile.confidence_score),
                    source_reference=f"phase5:{profile.capability_type}",
                )
                if len(response_terms) >= profile_budget:
                    break
            if len(response_terms) >= profile_budget:
                break

        # Fill remaining slots with deterministic ingredient terms from menu descriptions.
        menu_stmt = (
            select(MenuItem)
            .where(MenuItem.business_id == business_id)
            .order_by(MenuItem.extraction_confidence.desc(), MenuItem.id.asc())
        )
        menu_items = db.execute(menu_stmt).scalars().all()
        full_menu_item_names = _collect_menu_item_names(menu_items)
        description_blob = " ".join(
            item.description.strip()
            for item in menu_items
            if isinstance(item.description, str) and item.description.strip()
        )
        for ingredient_term in _extract_menu_description_terms(description_blob):
            _append_term(
                term=ingredient_term,
                confidence=0.78,
                source_reference="phase5:menu_description",
            )
            if len(response_terms) >= cap_limit:
                break

        # Fill any remaining slots with concrete menu item names.
        for item in menu_items:
            _append_term(
                term=str(item.item_name),
                confidence=float(item.extraction_confidence),
                source_reference="phase5:menu_item",
            )
            if len(response_terms) >= cap_limit:
                break

        if response_terms:
            return CapabilitiesResponse(
                business_id=business_id,
                capabilities=response_terms,
                menu_items=full_menu_item_names,
            )

        legacy_stmt = (
            select(BusinessCapability)
            .where(BusinessCapability.business_id == business_id)
            .order_by(BusinessCapability.confidence_score.desc())
            .limit(cap_limit)
        )
        legacy_capabilities = db.execute(legacy_stmt).scalars().all()
        return CapabilitiesResponse(
            business_id=business_id,
            capabilities=[
                CapabilityView(
                    ontology_term=item.ontology_term,
                    confidence_score=round(float(item.confidence_score), 3),
                    source_reference=item.source_reference,
                )
                for item in legacy_capabilities
            ],
            menu_items=full_menu_item_names,
        )

    def evidence_explanation(self, db: Session, business_id: int, query: str) -> EvidenceExplanationResponse | None:
        business = db.get(Business, business_id)
        if not business or business.embedding is None:
            return None

        expansion_chain = ontology_service.expand_query(db, query)
        terms = [query.strip()] + [term for term in expansion_chain if term.lower() != query.strip().lower()]
        vectors = self.embedding_service.encode_many(terms)

        semantic_matches: list[tuple[str, float]] = []
        for idx, vector in enumerate(vectors):
            stmt = (
                select((1 - Business.embedding.cosine_distance(vector)).label("similarity"))
                .where(Business.id == business_id)
                .where(Business.embedding.is_not(None))
            )
            similarity = db.execute(stmt).scalar_one_or_none()
            if similarity is None:
                continue
            semantic_matches.append((terms[idx], float(similarity)))

        semantic_matches.sort(key=lambda item: item[1], reverse=True)
        best_similarity = semantic_matches[0][1] if semantic_matches else 0.0

        cap_stmt = (
            select(BusinessCapability)
            .where(BusinessCapability.business_id == business_id)
            .order_by(BusinessCapability.confidence_score.desc())
            .limit(8)
        )
        capabilities = db.execute(cap_stmt).scalars().all()

        source_stmt = select(BusinessSource).where(BusinessSource.business_id == business_id)
        sources = db.execute(source_stmt).scalars().all()

        expansion_normalized = {term.lower() for term in expansion_chain}
        capability_matches: list[CapabilityView] = []
        for cap in capabilities:
            include = cap.ontology_term.lower() in expansion_normalized or len(capability_matches) < 4
            if include:
                capability_matches.append(
                    CapabilityView(
                        ontology_term=cap.ontology_term,
                        confidence_score=round(float(cap.confidence_score), 3),
                        source_reference=cap.source_reference,
                    )
                )

        semantic_lines = []
        for term, score in semantic_matches[:5]:
            semantic_lines.append(f"Semantic similarity match: {term} ({_clamp_score(score)}%)")

        return EvidenceExplanationResponse(
            business_id=business_id,
            query=query,
            evidence_score=_clamp_score(best_similarity),
            semantic_matches=semantic_lines,
            capability_matches=capability_matches,
            evidence_sources=[
                SourceView(
                    source_type=source.source_type,
                    source_url=source.source_url,
                    snippet=source.snippet,
                    last_fetched=source.last_fetched,
                )
                for source in sources
            ],
            last_updated=business.last_updated,
        )

    def business_model_debug(self, db: Session, business_id: int) -> dict | None:
        business = db.get(Business, business_id)
        if business is None:
            return None
        normalized = normalize_business_model_document(
            business.business_model if isinstance(business.business_model, dict) else None
        )
        return {
            "business_id": int(business.id),
            "name": business.name,
            "google_place_id": business.google_place_id,
            "primary_type": business.primary_type,
            "types": business.types if isinstance(business.types, list) else [],
            "business_model": normalized,
            "last_updated": business.last_updated,
        }

    def business_model_metrics(self, db: Session) -> dict:
        businesses = db.execute(select(Business.id, Business.business_model)).all()
        total = len(businesses)

        consumer_counts = {"true": 0, "false": 0, "null": 0}
        pure_service_area_true = 0
        missing_field_counts: dict[str, int] = {
            "consumer_facing": 0,
            "storefront.pure_service_area_business": 0,
            "fulfillment.delivery": 0,
            "fulfillment.takeout": 0,
            "fulfillment.dine_in": 0,
            "fulfillment.curbside_pickup": 0,
            "booking.reservable": 0,
            "operational.open_now": 0,
        }

        for _business_id, raw_model in businesses:
            normalized = normalize_business_model_document(raw_model if isinstance(raw_model, dict) else None)
            bm = normalized.get("business_model", {})

            consumer = bm.get("consumer_facing")
            if consumer is True:
                consumer_counts["true"] += 1
            elif consumer is False:
                consumer_counts["false"] += 1
            else:
                consumer_counts["null"] += 1

            storefront = bm.get("storefront", {})
            if storefront.get("pure_service_area_business") is True:
                pure_service_area_true += 1

            for key, path in {
                "consumer_facing": ("consumer_facing",),
                "storefront.pure_service_area_business": ("storefront", "pure_service_area_business"),
                "fulfillment.delivery": ("fulfillment", "delivery"),
                "fulfillment.takeout": ("fulfillment", "takeout"),
                "fulfillment.dine_in": ("fulfillment", "dine_in"),
                "fulfillment.curbside_pickup": ("fulfillment", "curbside_pickup"),
                "booking.reservable": ("booking", "reservable"),
                "operational.open_now": ("operational", "open_now"),
            }.items():
                current = bm
                missing = False
                for step in path:
                    if not isinstance(current, dict) or step not in current:
                        missing = True
                        break
                    current = current.get(step)
                if missing or current is None:
                    missing_field_counts[key] += 1

        missing_field_rates = {
            key: (round((count / total) * 100.0, 2) if total > 0 else 0.0)
            for key, count in missing_field_counts.items()
        }

        return {
            "total_businesses": total,
            "consumer_facing_distribution": consumer_counts,
            "pure_service_area_true": pure_service_area_true,
            "missing_field_counts": missing_field_counts,
            "missing_field_rates_pct": missing_field_rates,
        }


search_service = SearchService()
