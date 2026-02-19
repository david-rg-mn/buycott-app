from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.phase0_identity_lock.api_guard import enforce_identity_lock
from app.phase0_identity_lock.policy import build_search_policy
from app.phase1_semantic_pipeline.search import semantic_search
from app.phase2_transparency_ux.capabilities import capability_profile
from app.phase2_transparency_ux.suggestions import related_item_suggestions, search_suggestions
from app.phase2_transparency_ux.transparency import evidence_explanation, source_transparency
from app.schemas.api import (
    BusinessCapabilitiesResponse,
    CapabilityItem,
    EvidenceExplanationResponse,
    FilteredResultsResponse,
    RelatedItemsResponse,
    SearchResponse,
    SourceTransparencyResponse,
    SuggestionResponse,
)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    query: str = Query(min_length=2),
    lat: float = Query(),
    lng: float = Query(),
    include_chains: bool | None = Query(default=None),
    open_now: bool = Query(default=False),
    walking_distance: bool = Query(default=False),
    walking_threshold_minutes: int | None = Query(default=None, ge=1, le=60),
    limit: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
) -> SearchResponse:
    enforce_identity_lock(request)
    policy = build_search_policy(
        include_chains=include_chains,
        open_now=open_now,
        walking_distance=walking_distance,
        walking_threshold_minutes=walking_threshold_minutes,
    )
    return semantic_search(db=db, query=query, lat=lat, lng=lng, policy=policy, limit=limit)


@router.get("/search_suggestions", response_model=SuggestionResponse)
def suggestions(
    request: Request,
    query_prefix: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> SuggestionResponse:
    enforce_identity_lock(request)
    return SuggestionResponse(
        query_prefix=query_prefix,
        suggestions=search_suggestions(db, query_prefix),
    )


@router.get("/related_items", response_model=RelatedItemsResponse)
def related_items(
    request: Request,
    query: str = Query(min_length=2),
    db: Session = Depends(get_db),
) -> RelatedItemsResponse:
    enforce_identity_lock(request)
    return RelatedItemsResponse(query=query, related_items=related_item_suggestions(db, query))


@router.get("/evidence_explanation", response_model=EvidenceExplanationResponse)
def evidence(
    request: Request,
    business_id: uuid.UUID,
    query: str = Query(min_length=2),
    db: Session = Depends(get_db),
) -> EvidenceExplanationResponse:
    enforce_identity_lock(request)
    return evidence_explanation(db, business_id=business_id, query=query)


@router.get("/source_transparency", response_model=SourceTransparencyResponse)
def source_info(
    request: Request,
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SourceTransparencyResponse:
    enforce_identity_lock(request)
    return source_transparency(db, business_id=business_id)


@router.get("/business_capabilities", response_model=BusinessCapabilitiesResponse)
def business_capabilities(
    request: Request,
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BusinessCapabilitiesResponse:
    enforce_identity_lock(request)

    caps = capability_profile(db, business_id)
    return BusinessCapabilitiesResponse(
        business_id=business_id,
        likely_carries=[
            CapabilityItem(ontology_term=cap.ontology_term, confidence_score=cap.confidence_score)
            for cap in caps
        ],
    )


@router.get("/filter_local_only", response_model=FilteredResultsResponse)
def filter_local_only(
    request: Request,
    query: str,
    lat: float,
    lng: float,
    db: Session = Depends(get_db),
) -> FilteredResultsResponse:
    enforce_identity_lock(request)
    policy = build_search_policy(
        include_chains=False,
        open_now=False,
        walking_distance=False,
        walking_threshold_minutes=None,
    )
    response = semantic_search(db=db, query=query, lat=lat, lng=lng, policy=policy)
    return FilteredResultsResponse(filter_name="local_only", query=query, results=response.results)


@router.get("/filter_open_now", response_model=FilteredResultsResponse)
def filter_open_now(
    request: Request,
    query: str,
    lat: float,
    lng: float,
    include_chains: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FilteredResultsResponse:
    enforce_identity_lock(request)
    policy = build_search_policy(
        include_chains=include_chains,
        open_now=True,
        walking_distance=False,
        walking_threshold_minutes=None,
    )
    response = semantic_search(db=db, query=query, lat=lat, lng=lng, policy=policy)
    return FilteredResultsResponse(filter_name="open_now", query=query, results=response.results)


@router.get("/filter_walking_distance", response_model=FilteredResultsResponse)
def filter_walking_distance(
    request: Request,
    query: str,
    lat: float,
    lng: float,
    walking_threshold_minutes: int = Query(default=15, ge=1, le=60),
    include_chains: bool | None = Query(default=None),
    open_now: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> FilteredResultsResponse:
    enforce_identity_lock(request)
    policy = build_search_policy(
        include_chains=include_chains,
        open_now=open_now,
        walking_distance=True,
        walking_threshold_minutes=walking_threshold_minutes,
    )
    response = semantic_search(db=db, query=query, lat=lat, lng=lng, policy=policy)
    return FilteredResultsResponse(filter_name="walking_distance", query=query, results=response.results)
