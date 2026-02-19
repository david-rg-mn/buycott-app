# Buycott Backend

FastAPI service implementing:
- Phase 0 governance controls
- Phase 1 semantic L4 search pipeline
- Phase 2 transparency and accessibility features

## Run Locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/init_db.py
python scripts/seed_ontology.py
python scripts/seed_businesses.py

uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```

## Core Modules

- `app/phase0_identity_lock/` governance and API constraints
- `app/phase1_semantic_pipeline/` embeddings, ontology expansion, vector search
- `app/phase2_transparency_ux/` evidence explanations, suggestions, capabilities, accessibility
