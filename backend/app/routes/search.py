from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CapabilitiesResponse, EvidenceExplanationResponse, SearchResponse, SuggestionsResponse
from ..services.ontology_service import ontology_service
from ..services.search_service import SearchParams, search_service

router = APIRouter(tags=["search"])
FORBIDDEN_QUERY_PARAMS = {"rank_by", "priority", "sponsored", "promoted", "boost", "demote"}


def _coalesce_query(query: str | None, q: str | None) -> str:
    value = (query or q or "").strip()
    if not value:
        raise HTTPException(status_code=422, detail="Query is required via `query` or `q` parameter")
    return value


def _resolve_coordinates(location: str | None, lat: float | None, lng: float | None) -> tuple[float, float]:
    if lat is not None and lng is not None:
        return lat, lng

    if location:
        try:
            lat_raw, lng_raw = location.split(",", maxsplit=1)
            return float(lat_raw.strip()), float(lng_raw.strip())
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Location must be formatted as 'lat,lng'") from None

    raise HTTPException(status_code=422, detail="Provide coordinates via `lat`/`lng` or `location=lat,lng`")


def _assert_forbidden_params_absent(request: Request) -> None:
    query_keys = set(request.query_params.keys())
    forbidden_found = sorted(FORBIDDEN_QUERY_PARAMS.intersection(query_keys))
    if forbidden_found:
        raise HTTPException(
            status_code=400,
            detail=f"Forbidden query parameter(s): {', '.join(forbidden_found)}",
        )


@router.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    query: str | None = Query(default=None),
    q: str | None = Query(default=None),
    location: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    include_chains: bool = Query(default=False),
    open_now: bool = Query(default=False),
    walking_distance: bool = Query(default=False),
    walking_threshold_minutes: int = Query(default=15, ge=1, le=60),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    _assert_forbidden_params_absent(request)
    clean_query = _coalesce_query(query, q)
    resolved_lat, resolved_lng = _resolve_coordinates(location, lat, lng)
    params = SearchParams(
        query=clean_query,
        lat=resolved_lat,
        lng=resolved_lng,
        include_chains=include_chains,
        open_now=open_now,
        walking_distance=walking_distance,
        walking_threshold_minutes=walking_threshold_minutes,
        limit=limit,
    )
    return search_service.search(db, params)


@router.get("/businesses", response_model=SearchResponse)
def businesses(
    request: Request,
    location: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    include_chains: bool = Query(default=False),
    open_now: bool = Query(default=False),
    walking_distance: bool = Query(default=False),
    walking_threshold_minutes: int = Query(default=15, ge=1, le=60),
    limit: int = Query(default=1000, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> SearchResponse:
    _assert_forbidden_params_absent(request)
    resolved_lat, resolved_lng = _resolve_coordinates(location, lat, lng)
    params = SearchParams(
        query="all businesses",
        lat=resolved_lat,
        lng=resolved_lng,
        include_chains=include_chains,
        open_now=open_now,
        walking_distance=walking_distance,
        walking_threshold_minutes=walking_threshold_minutes,
        limit=limit,
    )
    return search_service.list_businesses(db, params)


@router.get("/search_suggestions", response_model=SuggestionsResponse)
def search_suggestions(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
) -> SuggestionsResponse:
    return SuggestionsResponse(query=q, suggestions=ontology_service.suggest(db, q, limit=limit))


@router.get("/business_capabilities/{business_id}", response_model=CapabilitiesResponse)
def business_capabilities(
    business_id: int,
    limit: int = Query(default=8, ge=1, le=30),
    db: Session = Depends(get_db),
) -> CapabilitiesResponse:
    return search_service.business_capabilities(db, business_id=business_id, limit=limit)


@router.get("/evidence_explanation", response_model=EvidenceExplanationResponse)
def evidence_explanation(
    business_id: int = Query(...),
    query: str = Query(...),
    db: Session = Depends(get_db),
) -> EvidenceExplanationResponse:
    result = search_service.evidence_explanation(db, business_id=business_id, query=query)
    if result is None:
        raise HTTPException(status_code=404, detail="Business or evidence data not found")
    return result


@router.get("/filter_local_only", response_model=SearchResponse)
def filter_local_only(
    request: Request,
    query: str | None = Query(default=None),
    q: str | None = Query(default=None),
    location: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    open_now: bool = Query(default=False),
    walking_distance: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> SearchResponse:
    _assert_forbidden_params_absent(request)
    clean_query = _coalesce_query(query, q)
    resolved_lat, resolved_lng = _resolve_coordinates(location, lat, lng)
    return search_service.search(
        db,
        SearchParams(
            query=clean_query,
            lat=resolved_lat,
            lng=resolved_lng,
            include_chains=False,
            open_now=open_now,
            walking_distance=walking_distance,
        ),
    )


@router.get("/filter_open_now", response_model=SearchResponse)
def filter_open_now(
    request: Request,
    query: str | None = Query(default=None),
    q: str | None = Query(default=None),
    location: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    include_chains: bool = Query(default=False),
    walking_distance: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> SearchResponse:
    _assert_forbidden_params_absent(request)
    clean_query = _coalesce_query(query, q)
    resolved_lat, resolved_lng = _resolve_coordinates(location, lat, lng)
    return search_service.search(
        db,
        SearchParams(
            query=clean_query,
            lat=resolved_lat,
            lng=resolved_lng,
            include_chains=include_chains,
            open_now=True,
            walking_distance=walking_distance,
        ),
    )


@router.get("/filter_walking_distance", response_model=SearchResponse)
def filter_walking_distance(
    request: Request,
    query: str | None = Query(default=None),
    q: str | None = Query(default=None),
    location: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    include_chains: bool = Query(default=False),
    open_now: bool = Query(default=False),
    walking_threshold_minutes: int = Query(default=15, ge=1, le=60),
    db: Session = Depends(get_db),
) -> SearchResponse:
    _assert_forbidden_params_absent(request)
    clean_query = _coalesce_query(query, q)
    resolved_lat, resolved_lng = _resolve_coordinates(location, lat, lng)
    return search_service.search(
        db,
        SearchParams(
            query=clean_query,
            lat=resolved_lat,
            lng=resolved_lng,
            include_chains=include_chains,
            open_now=open_now,
            walking_distance=True,
            walking_threshold_minutes=walking_threshold_minutes,
        ),
    )
