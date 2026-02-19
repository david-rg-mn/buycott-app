from dataclasses import dataclass

from app.config import get_settings


@dataclass(frozen=True)
class SearchPolicy:
    include_chains: bool
    open_now: bool
    walking_distance: bool
    walking_threshold_minutes: int


def build_search_policy(
    include_chains: bool | None,
    open_now: bool,
    walking_distance: bool,
    walking_threshold_minutes: int | None,
) -> SearchPolicy:
    settings = get_settings()
    resolved_include_chains = include_chains if include_chains is not None else not settings.local_only_default

    threshold = (
        walking_threshold_minutes
        if walking_threshold_minutes is not None
        else settings.walking_threshold_minutes_default
    )

    return SearchPolicy(
        include_chains=resolved_include_chains,
        open_now=open_now,
        walking_distance=walking_distance,
        walking_threshold_minutes=threshold,
    )
