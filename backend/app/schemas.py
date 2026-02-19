from datetime import datetime

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
    phone: str | None = None
    website: str | None = None
    open_now: bool
    badges: list[str]
    matched_terms: list[str]
    last_updated: datetime


class SearchResponse(BaseModel):
    query: str
    expansion_chain: list[str]
    related_items: list[str]
    local_only: bool
    filters: dict[str, bool | int]
    results: list[BusinessSearchResult]


class SuggestionsResponse(BaseModel):
    query: str
    suggestions: list[str]


class CapabilitiesResponse(BaseModel):
    business_id: int
    capabilities: list[CapabilityView]


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
