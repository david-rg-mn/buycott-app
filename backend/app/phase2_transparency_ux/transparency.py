from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Business, BusinessCapability, BusinessSource
from app.phase1_semantic_pipeline.embeddings import cosine_similarity, embedding_service
from app.phase1_semantic_pipeline.ontology import expand_query_hierarchy
from app.phase2_transparency_ux.evidence import (
    compute_evidence_strength,
    evidence_points,
)
from app.schemas.api import (
    EvidenceExplanationResponse,
    EvidencePoint,
    SourceItem,
    SourceTransparencyResponse,
)


def _load_business(db: Session, business_id: uuid.UUID) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business {business_id} not found",
        )
    return business


def source_transparency(db: Session, business_id: uuid.UUID) -> SourceTransparencyResponse:
    business = _load_business(db, business_id)
    sources = db.execute(
        select(BusinessSource).where(BusinessSource.business_id == business_id)
    ).scalars()

    return SourceTransparencyResponse(
        business_id=business_id,
        last_updated=business.last_updated,
        sources=[
            SourceItem(
                source_type=source.source_type,
                source_url=source.source_url,
                last_fetched=source.last_fetched,
            )
            for source in sources
        ],
    )


def evidence_explanation(
    db: Session,
    business_id: uuid.UUID,
    query: str,
) -> EvidenceExplanationResponse:
    business = _load_business(db, business_id)

    expansion = expand_query_hierarchy(db, query)
    query_embedding = embedding_service.embed_text(query)
    semantic_similarity = cosine_similarity(query_embedding, business.embedding)

    capabilities = list(
        db.execute(
            select(BusinessCapability)
            .where(BusinessCapability.business_id == business_id)
            .order_by(BusinessCapability.confidence_score.desc())
        ).scalars()
    )

    sources = list(
        db.execute(select(BusinessSource).where(BusinessSource.business_id == business_id)).scalars()
    )

    evidence = compute_evidence_strength(
        semantic_similarity=semantic_similarity,
        query=query,
        expanded_terms=expansion.expanded_terms,
        capabilities=capabilities,
    )

    points = evidence_points(
        query=query,
        expanded_terms=expansion.expanded_terms,
        capabilities=capabilities,
        sources=sources,
        semantic_similarity=semantic_similarity,
    )

    return EvidenceExplanationResponse(
        business_id=business_id,
        query=query,
        evidence_strength=evidence.evidence_strength,
        points=[EvidencePoint(label=label, detail=detail) for label, detail in points],
        ontology_match_chain=expansion.expanded_terms,
    )
