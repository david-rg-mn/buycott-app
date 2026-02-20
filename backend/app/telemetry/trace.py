from __future__ import annotations

import json
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID, uuid4

_TRACE_CONTEXT: ContextVar["SearchTrace | None"] = ContextVar("search_trace", default=None)


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)


@dataclass
class SearchTrace:
    request_id: UUID = field(default_factory=uuid4)
    path: str = ""
    method: str = "GET"
    request_start_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    query_text: str | None = None
    embedding_time_ms: float | None = None
    expansion_time_ms: float | None = None
    db_time_ms: float | None = None
    ranking_time_ms: float | None = None
    total_time_ms: float | None = None
    result_count: int | None = None
    top_similarity_score: float | None = None
    semantic_pipeline_active: bool = False
    _request_perf_counter_start: float = field(default_factory=perf_counter, repr=False)
    _recorded_stages: set[str] = field(default_factory=set, repr=False)

    def mark_query(self, query_text: str) -> None:
        self.query_text = query_text.strip()
        self.semantic_pipeline_active = True

    def record_stage_time(self, stage: str, duration_ms: float) -> None:
        if stage == "embedding":
            self._recorded_stages.add(stage)
            self.embedding_time_ms = (self.embedding_time_ms or 0.0) + duration_ms
        elif stage == "expansion":
            self._recorded_stages.add(stage)
            self.expansion_time_ms = (self.expansion_time_ms or 0.0) + duration_ms
        elif stage == "db":
            self._recorded_stages.add(stage)
            self.db_time_ms = (self.db_time_ms or 0.0) + duration_ms
        elif stage == "ranking":
            self._recorded_stages.add(stage)
            self.ranking_time_ms = (self.ranking_time_ms or 0.0) + duration_ms

    def set_result_summary(self, result_count: int, top_similarity_score: float | None) -> None:
        self.result_count = result_count
        if top_similarity_score is None:
            self.top_similarity_score = 0.0
            return
        self.top_similarity_score = min(1.0, max(0.0, float(top_similarity_score)))

    def finalize(self) -> None:
        if self.total_time_ms is None:
            elapsed_ms = (perf_counter() - self._request_perf_counter_start) * 1000.0
            self.total_time_ms = elapsed_ms

        if self.semantic_pipeline_active:
            if self.embedding_time_ms is None:
                self.embedding_time_ms = 0.0
            if self.expansion_time_ms is None:
                self.expansion_time_ms = 0.0
            if self.db_time_ms is None:
                self.db_time_ms = 0.0
            if self.ranking_time_ms is None:
                self.ranking_time_ms = 0.0
            if self.result_count is None:
                self.result_count = 0
            if self.top_similarity_score is None:
                self.top_similarity_score = 0.0

    def to_header_value(self) -> str:
        payload = {
            "request_id": str(self.request_id),
            "embedding_time_ms": _round_or_none(self.embedding_time_ms),
            "expansion_time_ms": _round_or_none(self.expansion_time_ms),
            "db_time_ms": _round_or_none(self.db_time_ms),
            "ranking_time_ms": _round_or_none(self.ranking_time_ms),
            "total_time_ms": _round_or_none(self.total_time_ms),
            "result_count": self.result_count,
            "top_similarity_score": _round_or_none(self.top_similarity_score),
        }
        return json.dumps(payload, separators=(",", ":"))

    def missing_required_stages(self) -> list[str]:
        if not self.semantic_pipeline_active:
            return []
        required = ("embedding", "expansion", "db", "ranking")
        return [stage for stage in required if stage not in self._recorded_stages]


def get_current_trace() -> SearchTrace | None:
    return _TRACE_CONTEXT.get()


def set_current_trace(trace: SearchTrace) -> Token:
    return _TRACE_CONTEXT.set(trace)


def reset_current_trace(token: Token) -> None:
    _TRACE_CONTEXT.reset(token)
