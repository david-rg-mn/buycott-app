.PHONY: backend-init backend-run backend-test openclaw-run docker-up docker-ingest

backend-init:
	cd backend && python scripts/init_db.py && python scripts/seed_ontology.py && python scripts/seed_businesses.py

backend-run:
	cd backend && uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && pytest

openclaw-run:
	python openclaw/run_openclaw.py

docker-up:
	docker compose up --build postgres backend

docker-ingest:
	docker compose --profile ingest up --build openclaw
