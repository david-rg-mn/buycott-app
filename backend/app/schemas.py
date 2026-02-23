from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceView(BaseModel):
    source_type: str
    source_url: str | None = None
    snippet: str | None = None
    last_fetched: datetime | None = None


class CapabilityView(BaseModel):
    ontology_term: str
    confidence_score: float
    source_reference: str | None = None


class BusinessSearchResult(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    distance_km: float
    minutes_away: int
    driving_minutes: int
    walking_minutes: int
    evidence_score: int = Field(ge=0, le=100)
    is_chain: bool
    chain_name: str | None = None
    formatted_address: str | None = None
    phone: str | None = None
    website: str | None = None
    hours: dict[str, Any] | None = None
    types: list[str] = Field(default_factory=list)
    open_now: bool
    badges: list[str]
    matched_terms: list[str]
    last_updated: datetime
    request_id: str | None = None


class SearchResponse(BaseModel):
    query: str
    expansion_chain: list[str]
    related_items: list[str]
    local_only: bool
    filters: dict[str, bool | int]
    results: list[BusinessSearchResult]
    request_id: str | None = None


class SuggestionsResponse(BaseModel):
    query: str
    suggestions: list[str]


class CapabilitiesResponse(BaseModel):
    business_id: int
    capabilities: list[CapabilityView]
    menu_items: list[str] = Field(default_factory=list)


class EvidenceExplanationResponse(BaseModel):
    business_id: int
    query: str
    evidence_score: int
    semantic_matches: list[str]
    capability_matches: list[CapabilityView]
    evidence_sources: list[SourceView]
    last_updated: datetime


class HealthResponse(BaseModel):
    status: str


class HealthMetricsResponse(BaseModel):
    sample_size: int
    avg_embedding_time_ms: float
    avg_db_time_ms: float
    avg_ranking_time_ms: float
    avg_expansion_time_ms: float
    avg_total_time_ms: float


class VerifiedClaimRecord(BaseModel):
    claim_id: str
    label: str
    evidence: list[dict[str, Any]]
    confidence: float = Field(ge=0, le=1)
    timestamp: datetime


class PrecisionSearchResult(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    distance_km: float
    minutes_away: int
    driving_minutes: int
    walking_minutes: int
    open_now: bool
    is_chain: bool
    chain_name: str | None = None
    precision_score: float = Field(ge=0, le=1)
    evidence_score: int = Field(ge=0, le=100)
    verified_claims: list[VerifiedClaimRecord]
    audit_chain: dict[str, Any]
    last_updated: datetime


class PrecisionSearchResponse(BaseModel):
    query: str
    normalized_query: str
    matched_concepts: list[str]
    results: list[PrecisionSearchResult]


class VerifiedClaimsResponse(BaseModel):
    business_id: int
    claims: list[VerifiedClaimRecord]


class BusinessModelDebugResponse(BaseModel):
    business_id: int
    name: str
    google_place_id: str | None = None
    primary_type: str | None = None
    types: list[str]
    business_model: dict[str, Any]
    last_updated: datetime


class BusinessModelMetricsResponse(BaseModel):
    total_businesses: int
    consumer_facing_distribution: dict[str, int]
    pure_service_area_true: int
    missing_field_counts: dict[str, int]
    missing_field_rates_pct: dict[str, float]
