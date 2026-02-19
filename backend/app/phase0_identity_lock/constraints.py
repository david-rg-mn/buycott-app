SYSTEM_IDENTITY = "semantic geographic capability index"

FORBIDDEN_SCHEMA_FIELDS = {
    "popularity_score",
    "click_count",
    "engagement_metric",
    "paid_priority",
    "sponsored_flag",
    "conversion_rate",
    "revenue_metric",
}

ALLOWED_SEARCH_PARAMS = {
    "query",
    "lat",
    "lng",
    "include_chains",
    "open_now",
    "walking_distance",
    "walking_threshold_minutes",
    "limit",
}

FORBIDDEN_API_PARAMS = {
    "rank_by",
    "priority",
    "sponsored",
    "promoted",
    "boost",
    "demote",
}

MAX_ONTOLOGY_DEPTH = 5
MIN_ONTOLOGY_DEPTH = 3
