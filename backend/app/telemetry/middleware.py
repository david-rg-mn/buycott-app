from __future__ import annotations

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..config import settings
from .logging_utils import PERF_LEVEL_NUM
from .repository import persist_trace
from .trace import SearchTrace, reset_current_trace, set_current_trace

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("buycott.perf")


class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace = SearchTrace(path=request.url.path, method=request.method)
        request.state.request_id = str(trace.request_id)
        token = set_current_trace(trace)

        response: Response | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            trace.finalize()
            if response is not None and request.url.path.startswith("/api/"):
                response.headers["X-Search-Performance"] = trace.to_header_value()
                response.headers["X-Request-Id"] = str(trace.request_id)

            self._log_trace(trace, status_code)
            if settings.telemetry_enabled:
                persist_trace(trace)
            reset_current_trace(token)

    def _log_trace(self, trace: SearchTrace, status_code: int) -> None:
        if not trace.semantic_pipeline_active:
            return

        missing_stages = trace.missing_required_stages()
        if missing_stages:
            logger.warning(
                "Search trace missing stage timing(s): %s",
                ", ".join(missing_stages),
                extra={"request_id": str(trace.request_id)},
            )

        perf_logger.log(
            PERF_LEVEL_NUM,
            "search_trace request_id=%s status=%s query=%r embedding_ms=%s expansion_ms=%s db_ms=%s ranking_ms=%s total_ms=%s results=%s top_similarity=%s",
            trace.request_id,
            status_code,
            trace.query_text,
            trace.embedding_time_ms,
            trace.expansion_time_ms,
            trace.db_time_ms,
            trace.ranking_time_ms,
            trace.total_time_ms,
            trace.result_count,
            trace.top_similarity_score,
        )
