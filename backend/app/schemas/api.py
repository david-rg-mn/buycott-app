from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    business_id: uuid.UUID
    name: str
    lat: float
    lng: float
    minutes_away: int
    walking_minutes: int
    driving_minutes: int
    distance_km: float
    evidence_strength: int
    semantic_similarity: float
    ontology_bonus: float
    explicit_evidence_bonus: float
    is_chain: bool
    chain_name: str | None
    independent_badge: bool
    specialist_badge: bool
    capability_preview: list[str]
    source_types: list[str]
    last_updated: datetime


class SearchResponse(BaseModel):
    query: str
    expanded_terms: list[str]
    local_only: bool
    open_now: bool
    walking_distance: bool
    results: list[SearchResult]


class SuggestionResponse(BaseModel):
    query_prefix: str
    suggestions: list[str]


class RelatedItemsResponse(BaseModel):
    query: str
    related_items: list[str]


class EvidencePoint(BaseModel):
    label: str
    detail: str


class EvidenceExplanationResponse(BaseModel):
    business_id: uuid.UUID
    query: str
    evidence_strength: int
    points: list[EvidencePoint]
    ontology_match_chain: list[str]


class SourceItem(BaseModel):
    source_type: str
    source_url: str
    last_fetched: datetime


class SourceTransparencyResponse(BaseModel):
    business_id: uuid.UUID
    last_updated: datetime
    sources: list[SourceItem]


class CapabilityItem(BaseModel):
    ontology_term: str
    confidence_score: float


class BusinessCapabilitiesResponse(BaseModel):
    business_id: uuid.UUID
    likely_carries: list[CapabilityItem]


class FilteredResultsResponse(BaseModel):
    filter_name: str
    query: str
    results: list[SearchResult]
