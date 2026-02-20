Buycott Observability Integration Memo

Phase 1: Observability and Telemetry
Version: Implemented Integration Update
Date: February 20, 2026
Status: Implemented in current codebase

1. Purpose

This memo records the Phase 1 observability integration that instruments the semantic search pipeline as a first-class architectural concern.

The goal is to ensure every search request is measurable, debuggable, and traceable end-to-end without changing core semantic behavior.

2. Scope

This update covers:

- Backend telemetry middleware/decorator instrumentation
- Telemetry persistence in PostgreSQL
- Response performance headers
- Aggregated metrics health endpoint
- Frontend request trace propagation to map pins and detail UI
- Environment-level logging controls (DEBUG, INFO, PERF)

3. Implemented Architecture

Telemetry is implemented as a cross-cutting layer, isolated from semantic decision logic.

Pipeline stage instrumentation points:

1. API controller entry: request trace created with request_start_timestamp and request_id
2. Ontology service path: expansion_time_ms
3. Embedding service path: embedding_time_ms
4. Database repository path (pgvector + capability/source fetches): db_time_ms
5. Ranking/evidence engine path: ranking_time_ms
6. API controller exit: total_time_ms, headers emitted, trace persisted

4. Backend Modules Added

New telemetry module:

- backend/app/telemetry/__init__.py
- backend/app/telemetry/trace.py
- backend/app/telemetry/instrumentation.py
- backend/app/telemetry/middleware.py
- backend/app/telemetry/repository.py
- backend/app/telemetry/logging_utils.py

Core integration points:

- backend/app/main.py
- backend/app/services/search_service.py
- backend/app/models.py
- backend/app/schemas.py
- backend/app/config.py

5. Search Trace Object Contract

Each semantic search request generates a structured trace with:

- request_id (UUID)
- query_text
- embedding_time_ms
- expansion_time_ms
- db_time_ms
- ranking_time_ms
- total_time_ms
- result_count
- top_similarity_score
- request_start_timestamp

Strict stage coverage behavior:

- Required stages: embedding, expansion, db, ranking
- Missing stage coverage is logged as a warning for regression detection

6. Telemetry Persistence Schema

Implemented table in PostgreSQL:

CREATE TABLE telemetry_logs (
    request_id UUID PRIMARY KEY,
    query_text TEXT,
    embedding_time_ms DOUBLE PRECISION,
    expansion_time_ms DOUBLE PRECISION,
    db_time_ms DOUBLE PRECISION,
    ranking_time_ms DOUBLE PRECISION,
    total_time_ms DOUBLE PRECISION,
    result_count INTEGER,
    top_similarity_score DOUBLE PRECISION,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

Also added:

- index on telemetry_logs(timestamp DESC)

7. API Contract Changes

7.1 Response headers

All /api/* responses include:

- X-Search-Performance: JSON payload with request_id and stage timings
- X-Request-Id: request UUID

7.2 New health metrics endpoint

- GET /health/metrics

Returns aggregated averages from telemetry_logs:

- avg_embedding_time_ms
- avg_db_time_ms
- avg_ranking_time_ms
- avg_expansion_time_ms
- avg_total_time_ms
- sample_size

7.3 Search response trace fields

Search payload now includes:

- request_id at response level
- request_id on each result row

8. Frontend Traceability Integration (Flutter)

Implemented in:

- frontend/buycott_flutter/lib/services/api_service.dart
- frontend/buycott_flutter/lib/models/api_models.dart
- frontend/buycott_flutter/lib/main.dart

Behavior:

- API client parses X-Search-Performance header
- request_id and timing payload are attached to SearchPayload/SearchResult
- each map pin can be traced to request_id
- request_id displayed in business sheet
- top panel shows compact trace and API latency summary
- "Time-to-possession" surfaced explicitly in business detail panel

9. Configuration and Runtime Controls

Added env configuration:

- BUYCOTT_LOG_LEVEL=INFO
- BUYCOTT_PERF_LOG_LEVEL=PERF
- BUYCOTT_TELEMETRY_ENABLED=true

These map to backend settings and control:

- base application logging level
- performance telemetry logging level
- telemetry persistence toggle

10. Deterministic Optimization Signals

This update ensures ranking/model changes can be evaluated with persisted evidence:

- top_similarity_score captured per request
- result_count captured per request
- stage latencies captured per request

This supports semantic drift detection and evidence-based optimization decisions.

11. Verification Summary

Validation executed during integration:

- backend tests: pytest passed
- backend compile check: python -m compileall app passed
- flutter static analysis: flutter analyze passed
- flutter widget tests: flutter test passed

Note: Flutter tests may log OpenStreetMap tile request warnings in test environment; this does not fail tests.

12. Operational Runbook

1. Apply schema update:
   python3 pipeline/init_db.py

2. Verify telemetry table:
   SELECT COUNT(*) FROM telemetry_logs;

3. Run a search request:
   curl -i "http://localhost:8000/api/search?query=usb-c%20cable&lat=44.9778&lng=-93.2650"

4. Confirm headers:
   X-Search-Performance
   X-Request-Id

5. Confirm metrics endpoint:
   curl http://localhost:8000/health/metrics

13. Compliance Statement

The observability layer is now integrated as a non-invasive architectural concern.

Semantic pipeline timing is captured across all required stages, persisted to telemetry_logs, exposed via response headers, and surfaced in frontend request traceability for map-level debugging.
