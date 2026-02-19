.PHONY: db-up db-down backend-install api pipeline pipeline-local pipeline-docker mobile test

db-up:
	docker compose up -d db

db-down:
	docker compose down

backend-install:
	python3 -m pip install -r backend/requirements.txt

api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pipeline:
	python3 pipeline/run_full_pipeline.py

pipeline-local:
	python3 pipeline/run_full_pipeline.py --mode local

pipeline-docker:
	python3 pipeline/run_full_pipeline.py --mode docker

mobile:
	cd frontend/buycott_flutter && flutter run --dart-define=BUYCOTT_API_URL=http://localhost:8000

test:
	cd backend && pytest
