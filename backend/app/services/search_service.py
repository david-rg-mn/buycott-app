from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Business, BusinessCapability, BusinessSource
from ..schemas import (
    BusinessSearchResult,
    CapabilitiesResponse,
    CapabilityView,
    EvidenceExplanationResponse,
    SearchResponse,
    SourceView,
)
from .distance_service import compute_travel_minutes, haversine_km
from .embedding_service import get_embedding_service
from .ontology_service import ontology_service
from .time_service import is_open_now


@dataclass
class SearchParams:
    query: str
    lat: float
    lng: float
    include_chains: bool = False
    open_now: bool = False
    walking_distance: bool = False
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

    def search(self, db: Session, params: SearchParams) -> SearchResponse:
        clean_query = params.query.strip()
        if not clean_query:
            return SearchResponse(
                query=params.query,
                expansion_chain=[],
                related_items=[],
                local_only=not params.include_chains,
                filters={
                    "include_chains": params.include_chains,
                    "open_now": params.open_now,
                    "walking_distance": params.walking_distance,
                    "walking_threshold_minutes": params.walking_threshold_minutes,
                },
                results=[],
            )

        expansion_chain = ontology_service.expand_query(db, clean_query)
        query_terms = [clean_query]
        for term in expansion_chain:
            if term.lower() not in {existing.lower() for existing in query_terms}:
                query_terms.append(term)

        vectors = self.embedding_service.encode_many(query_terms)
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

        if not candidate_map:
            return SearchResponse(
                query=clean_query,
                expansion_chain=expansion_chain,
                related_items=ontology_service.related_items(db, clean_query),
                local_only=not params.include_chains,
                filters={
                    "include_chains": params.include_chains,
                    "open_now": params.open_now,
                    "walking_distance": params.walking_distance,
                    "walking_threshold_minutes": params.walking_threshold_minutes,
                },
                results=[],
            )

        business_ids = list(candidate_map.keys())
        capabilities_map = _fetch_capabilities(db, business_ids)
        _ = _fetch_sources(db, business_ids)

        result_rows: list[BusinessSearchResult] = []

        for candidate in candidate_map.values():
            if candidate.similarity < settings.min_similarity:
                continue

            business = candidate.business
            distance_km = haversine_km(params.lat, params.lng, business.lat, business.lng)
            walking_minutes, driving_minutes, fastest_minutes = compute_travel_minutes(distance_km)

            if params.walking_distance and walking_minutes > params.walking_threshold_minutes:
                continue

            open_flag = is_open_now(business.hours_json, business.timezone)
            if params.open_now and not open_flag:
                continue

            badges: list[str] = []
            if not business.is_chain:
                badges.append("Independent")

            caps = capabilities_map.get(business.id, [])
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
                    evidence_score=_clamp_score(candidate.similarity),
                    is_chain=business.is_chain,
                    chain_name=business.chain_name,
                    phone=business.phone,
                    website=business.website,
                    open_now=open_flag,
                    badges=badges,
                    matched_terms=sorted(candidate.matched_terms),
                    last_updated=business.last_updated,
                )
            )

        result_rows.sort(key=lambda item: (item.distance_km, item.name.lower()))

        return SearchResponse(
            query=clean_query,
            expansion_chain=expansion_chain,
            related_items=ontology_service.related_items(db, clean_query),
            local_only=not params.include_chains,
            filters={
                "include_chains": params.include_chains,
                "open_now": params.open_now,
                "walking_distance": params.walking_distance,
                "walking_threshold_minutes": params.walking_threshold_minutes,
            },
            results=result_rows[: params.limit],
        )

    def business_capabilities(self, db: Session, business_id: int, limit: int = 8) -> CapabilitiesResponse:
        stmt = (
            select(BusinessCapability)
            .where(BusinessCapability.business_id == business_id)
            .order_by(BusinessCapability.confidence_score.desc())
            .limit(limit)
        )
        capabilities = db.execute(stmt).scalars().all()
        return CapabilitiesResponse(
            business_id=business_id,
            capabilities=[
                CapabilityView(
                    ontology_term=item.ontology_term,
                    confidence_score=round(float(item.confidence_score), 3),
                    source_reference=item.source_reference,
                )
                for item in capabilities
            ],
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


search_service = SearchService()
