# Buycott

Buycott is a semantic, map-first civic discovery app for finding where an item can likely be obtained nearby.

This repository now contains a working Phase 0-5 vertical slice implementation:

- `FastAPI` backend API
- `PostgreSQL + pgvector` schema
- Google Places ingestion + embedding + capability mapping pipeline
- OpenClaw Phase 5 multi-agent router/scraper/inference pipeline for menu and business signals
- Ontology expansion and semantic vector search
- Flutter map-first client with evidence/explainability features

## Architecture

Implementation aligns with:

- `seed_docs/README.md`
- `seed_docs/phase-summary.md`
- `seed_docs/phase0.md`
- `seed_docs/phase1.md`
- `seed_docs/phase2.md`
- `seed_docs/tecbincal-architectural-blueprint.md`

Key invariant enforcement:

- Local-first default (`include_chains=false`)
- No monetization/popularity/ranking fields
- Evidence score is transparency-only
- Search ordering by geographic distance
- Ontology expansion depth constrained (default `4`)

## Repo Layout

- `backend/` FastAPI API and search services
- `database/schema.sql` pgvector schema + indexes
- `data/raw/` seed ontology and extracted public business text
- `pipeline/` ingestion, embedding, and capability scripts
- `frontend/buycott_flutter/` Flutter app
- `seed_docs/` original architecture documents

## Prerequisites

- Docker Desktop (or Docker Engine) running locally
- Python 3.9+
- Flutter SDK (for mobile app only)

## Quick Start

### 1. Start database and API with Docker

```bash
docker compose up --build -d
```

### 2. Run baseline pipeline (Google seed + embeddings + capabilities)

```bash
python3 pipeline/run_full_pipeline.py --seed-google
```

`run_full_pipeline.py` defaults to `--mode auto`:

- Uses local Python packages if available
- Falls back to the running Docker `api` service if local packages are missing

If you need to re-apply schema first:

```bash
python3 pipeline/run_full_pipeline.py --with-schema --seed-google
```

Before running Google ingestion, set `GOOGLE_MAPS_API_KEY` in `.env`.

### 2b. Run Phase 5 OpenClaw enrichment (router + subagents + normalization)

```bash
python3 pipeline/run_full_pipeline.py --seed-google --phase5-openclaw
```

This executes:
- Router master modality detection (`html`, `spa`, `pdf`, `image`, `api`, `social`)
- `sessions.spawn`-style scraper fanout
- Layer 2 ontology normalization and canonical capability assembly
- Per-item + final business embedding updates for pgvector cosine search

By default, Phase 5 enforces Docker sandbox execution. For explicit local override:

```bash
python3 pipeline/phase5_openclaw_pipeline.py --allow-host-execution --limit 5
```

### 3. Verify backend

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/search?query=usb-c%20to%20lightning%20cable&lat=44.9778&lng=-93.2650"
```

## Local Backend Run (without Docker)

1. Create Postgres DB with pgvector.
2. Set env vars from `backend/.env.example`.
3. Install dependencies:

```bash
python3 -m pip install -r backend/requirements.txt
```

4. Apply schema and run pipeline:

```bash
python3 pipeline/init_db.py
python3 pipeline/run_full_pipeline.py --mode local
```

5. Start API:

```bash
cd backend && uvicorn app.main:app --reload
```

## Flutter App

```bash
cd frontend/buycott_flutter
flutter pub get
flutter run --dart-define=BUYCOTT_API_URL=http://localhost:8000
```

If `flutter` is not found, install Flutter SDK and add it to your shell `PATH`.

Main implemented UI/features:

- Full-screen map with semantic pins
- Time-to-possession pin metric (minutes-away) with traceable request IDs
- Search + ontology suggestions
- Local-only toggle (default on)
- Open-now + walking-distance filters
- Evidence score square (minutes + confidence)
- Evidence explanation panel
- Capability discovery panel
- Independent + specialist badges
- Related-item ontology suggestions

## Backend Endpoints

- `GET /health`
- `GET /health/metrics`
- `GET /api/search`
- `GET /api/search_suggestions`
- `GET /api/evidence_explanation`
- `GET /api/business_capabilities/{business_id}`
- `GET /api/filter_local_only`
- `GET /api/filter_open_now`
- `GET /api/filter_walking_distance`

All `/api/*` responses now include:

- `X-Search-Performance`: structured stage timings (`embedding`, `expansion`, `db`, `ranking`, `total`)
- `X-Request-Id`: request trace identifier that maps to `telemetry_logs.request_id`

## Pipeline Commands

- `python3 pipeline/init_db.py`
- `python3 pipeline/load_ontology.py`
- `python3 pipeline/google_places_seed.py`
- `python3 pipeline/phase5_openclaw_pipeline.py`
- `python3 pipeline/build_embeddings.py`
- `python3 pipeline/rebuild_capabilities.py`
- `python3 pipeline/run_full_pipeline.py --seed-google`
- `python3 pipeline/run_full_pipeline.py --seed-google --phase5-openclaw`
- `python3 pipeline/run_full_pipeline.py --mode local`
- `python3 pipeline/run_full_pipeline.py --mode docker --seed-google`

Sub-agent manual spawn entrypoint:

- `./subagents spawn html-scraper --source-url https://example.com/menu --source-type website --allow-host-execution`

## Testing

```bash
cd backend
pytest
```
