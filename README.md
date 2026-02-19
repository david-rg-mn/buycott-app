# Buycott Implementation (Phases 0-2)

Buycott is implemented as a **semantic geographic capability index**.

This repo now contains the full layered system described by the blueprint docs:
- Phase 0: Identity lock, governance, forbidden ranking controls
- Phase 1: L4 semantic query pipeline with ontology expansion + pgvector similarity
- Phase 2: Transparency, capability visualization, semantic suggestions, local/open/walking filters

## Architecture Layers

- `backend/app/phase0_identity_lock/`
- `backend/app/phase1_semantic_pipeline/`
- `backend/app/phase2_transparency_ux/`

Strict layering is enforced by design:
- Phase 0 modules validate policy/parameters and prevent ranking controls.
- Phase 1 modules execute embeddings, deterministic ontology expansion (3-5 levels), and vector search.
- Phase 2 modules add transparency outputs, evidence explanations, capability views, and accessibility filters.

## Repository Structure

- `backend/` FastAPI + PostgreSQL/pgvector semantic API
- `openclaw/` extraction agents and ingestion pipeline
- `frontend/` Flutter map-first client with gradient pin UX and bottom sheets
- `infra/postgres/init.sql` pgvector schema initialization
- `blueprints/` original specification documents

## Data Flow

### Extraction Pipeline
1. Public sources (`openclaw/config/public_sources.json`)
2. OpenClaw agent extraction (`openclaw/agents/public_business_agent.py`)
3. Text extraction + cleaning
4. Embedding generation (`phase1_semantic_pipeline/embeddings.py`)
5. PostgreSQL/pgvector storage (`businesses`, `business_sources`, `business_capabilities`)

### Search Pipeline
1. User query
2. Query embedding
3. Ontology expansion (parent-only, deterministic, 3-5 levels)
4. Expanded vector search against `businesses.embedding`
5. Local-first filtering (`is_chain=false` default)
6. Open-now / walking-distance filters (optional)
7. Distance sorting (no popularity/revenue ranking)
8. Result assembly with evidence strength + minutes away

## Database Models

Implemented core schema in `infra/postgres/init.sql` and `backend/app/db/models.py`:
- `businesses`
- `ontology_terms`
- `business_sources`
- `business_capabilities`
- `business_hours`

## API Surface

Core endpoints:
- `GET /search`
- `GET /search_suggestions`
- `GET /related_items`
- `GET /evidence_explanation`
- `GET /source_transparency`
- `GET /business_capabilities`
- `GET /filter_local_only`
- `GET /filter_open_now`
- `GET /filter_walking_distance`

Evidence score is exposed for transparency only; ordering is distance-based.

## Quick Start

1. Copy env values:
```bash
cp .env.example .env
```

2. Start database + backend:
```bash
docker compose up --build postgres backend
```

3. Run OpenClaw ingestion (optional profile, one-shot):
```bash
docker compose --profile ingest up --build openclaw
```

4. Run Flutter app:
```bash
cd frontend
flutter pub get
flutter run --dart-define=BUYCOTT_API_URL=http://localhost:8000
```

## Governance Guarantees

The backend enforces Phase 0 identity lock:
- Forbidden query params (`rank_by`, `boost`, `promoted`, etc.) are rejected.
- Default search policy is local-first (`include_chains=false`).
- No schema fields for popularity/engagement/monetization ranking are present.
- Ontology expansion is parent-only and acyclic.
