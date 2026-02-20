from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import TelemetryLog
from .trace import SearchTrace

logger = logging.getLogger(__name__)


def persist_trace(trace: SearchTrace) -> None:
    if not trace.semantic_pipeline_active:
        return

    row = TelemetryLog(
        request_id=trace.request_id,
        query_text=trace.query_text,
        embedding_time_ms=trace.embedding_time_ms,
        expansion_time_ms=trace.expansion_time_ms,
        db_time_ms=trace.db_time_ms,
        ranking_time_ms=trace.ranking_time_ms,
        total_time_ms=trace.total_time_ms,
        result_count=trace.result_count,
        top_similarity_score=trace.top_similarity_score,
        timestamp=trace.request_start_timestamp.replace(tzinfo=None),
    )

    try:
        with SessionLocal() as session:
            session.merge(row)
            session.commit()
    except Exception:
        logger.exception("Failed to persist telemetry trace", extra={"request_id": str(trace.request_id)})


def _to_float(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 3)


def fetch_average_latency_metrics(db: Session) -> dict[str, float | int]:
    stmt = select(
        func.count(TelemetryLog.request_id).label("sample_size"),
        func.avg(TelemetryLog.embedding_time_ms).label("avg_embedding_time_ms"),
        func.avg(TelemetryLog.db_time_ms).label("avg_db_time_ms"),
        func.avg(TelemetryLog.ranking_time_ms).label("avg_ranking_time_ms"),
        func.avg(TelemetryLog.expansion_time_ms).label("avg_expansion_time_ms"),
        func.avg(TelemetryLog.total_time_ms).label("avg_total_time_ms"),
    )
    try:
        row = db.execute(stmt).one()
    except Exception:
        logger.exception("Failed to read telemetry metrics")
        return {
            "sample_size": 0,
            "avg_embedding_time_ms": 0.0,
            "avg_db_time_ms": 0.0,
            "avg_ranking_time_ms": 0.0,
            "avg_expansion_time_ms": 0.0,
            "avg_total_time_ms": 0.0,
        }

    return {
        "sample_size": int(row.sample_size or 0),
        "avg_embedding_time_ms": _to_float(row.avg_embedding_time_ms),
        "avg_db_time_ms": _to_float(row.avg_db_time_ms),
        "avg_ranking_time_ms": _to_float(row.avg_ranking_time_ms),
        "avg_expansion_time_ms": _to_float(row.avg_expansion_time_ms),
        "avg_total_time_ms": _to_float(row.avg_total_time_ms),
    }
