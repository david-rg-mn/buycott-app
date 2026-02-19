from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Business, BusinessCapability, BusinessHour, BusinessSource, OntologyTerm
from app.phase0_identity_lock.policy import SearchPolicy
from app.phase1_semantic_pipeline.embeddings import embedding_service
from app.phase1_semantic_pipeline.ontology import expand_query_hierarchy
from app.phase2_transparency_ux.accessibility import compute_travel_metrics, is_open_now
from app.phase2_transparency_ux.capabilities import is_specialist_business
from app.phase2_transparency_ux.evidence import compute_evidence_strength
from app.schemas.api import SearchResponse, SearchResult


def _expanded_embeddings(db: Session, expanded_terms: list[str]) -> list[list[float]]:
    term_embeddings = {
        term: embedding
        for term, embedding in db.execute(
            select(OntologyTerm.term, OntologyTerm.embedding).where(OntologyTerm.term.in_(expanded_terms))
        ).all()
    }

    output: list[list[float]] = []
    for term in expanded_terms:
        ontology_embedding = term_embeddings.get(term)
        if ontology_embedding is None:
            output.append(embedding_service.embed_text(term))
        else:
            output.append(ontology_embedding)
    return output


def semantic_search(
    db: Session,
    query: str,
    lat: float,
    lng: float,
    policy: SearchPolicy,
    limit: int = 30,
) -> SearchResponse:
    expansion = expand_query_hierarchy(db, query)
    expanded_terms = expansion.expanded_terms
    embeddings = _expanded_embeddings(db, expanded_terms)

    candidate_by_id: dict[uuid.UUID, tuple[Business, float]] = {}

    for vector in embeddings:
        distance_expr = Business.embedding.cosine_distance(vector)
        similarity_expr = (1 - distance_expr).label("similarity")

        stmt = select(Business, similarity_expr).order_by(distance_expr).limit(limit * 5)
        if not policy.include_chains:
            stmt = stmt.where(Business.is_chain.is_(False))

        rows = db.execute(stmt).all()

        for business, similarity in rows:
            existing = candidate_by_id.get(business.id)
            if existing is None or similarity > existing[1]:
                candidate_by_id[business.id] = (business, float(similarity))

    if not candidate_by_id:
        return SearchResponse(
            query=query,
            expanded_terms=expanded_terms,
            local_only=not policy.include_chains,
            open_now=policy.open_now,
            walking_distance=policy.walking_distance,
            results=[],
        )

    business_ids = list(candidate_by_id.keys())

    capability_rows = db.execute(
        select(BusinessCapability)
        .where(BusinessCapability.business_id.in_(business_ids))
        .order_by(BusinessCapability.confidence_score.desc())
    ).scalars()
    capabilities_by_business: dict[uuid.UUID, list[BusinessCapability]] = defaultdict(list)
    for cap in capability_rows:
        capabilities_by_business[cap.business_id].append(cap)

    source_rows = db.execute(
        select(BusinessSource).where(BusinessSource.business_id.in_(business_ids))
    ).scalars()
    sources_by_business: dict[uuid.UUID, list[BusinessSource]] = defaultdict(list)
    for source in source_rows:
        sources_by_business[source.business_id].append(source)

    hours_rows = db.execute(select(BusinessHour).where(BusinessHour.business_id.in_(business_ids))).scalars()
    hours_by_business: dict[uuid.UUID, list[BusinessHour]] = defaultdict(list)
    for hour in hours_rows:
        hours_by_business[hour.business_id].append(hour)

    assembled: list[SearchResult] = []

    for business_id, (business, similarity) in candidate_by_id.items():
        travel = compute_travel_metrics(lat, lng, business.lat, business.lng)

        if policy.walking_distance and travel.walking_minutes > policy.walking_threshold_minutes:
            continue

        business_hours = hours_by_business.get(business_id, [])
        if policy.open_now and not is_open_now(business_hours):
            continue

        business_caps = capabilities_by_business.get(business_id, [])
        evidence = compute_evidence_strength(
            semantic_similarity=similarity,
            query=query,
            expanded_terms=expanded_terms,
            capabilities=business_caps,
        )

        preview = [cap.ontology_term for cap in business_caps[:4]]
        specialist = is_specialist_business(db, business_caps)

        assembled.append(
            SearchResult(
                business_id=business.id,
                name=business.name,
                lat=business.lat,
                lng=business.lng,
                minutes_away=travel.minutes_away,
                walking_minutes=travel.walking_minutes,
                driving_minutes=travel.driving_minutes,
                distance_km=round(travel.distance_km, 3),
                evidence_strength=evidence.evidence_strength,
                semantic_similarity=round(evidence.semantic_similarity, 4),
                ontology_bonus=round(evidence.ontology_bonus, 4),
                explicit_evidence_bonus=round(evidence.explicit_evidence_bonus, 4),
                is_chain=business.is_chain,
                chain_name=business.chain_name,
                independent_badge=not business.is_chain,
                specialist_badge=specialist,
                capability_preview=preview,
                source_types=sorted({src.source_type for src in sources_by_business.get(business_id, [])}),
                last_updated=business.last_updated,
            )
        )

    assembled.sort(key=lambda row: row.distance_km)

    return SearchResponse(
        query=query,
        expanded_terms=expanded_terms,
        local_only=not policy.include_chains,
        open_now=policy.open_now,
        walking_distance=policy.walking_distance,
        results=assembled[:limit],
    )
