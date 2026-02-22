Steps I did:

1. Start Docker Desktop.
2. Bring up backend + DB:

  cd /Users/davidrangelgarcia/Documents/GitHub/buycott-app
  docker compose up --build -d

3. Seed data (so search returns real results):

  docker exec buycott-api python /workspace/pipeline/run_full_pipeline.py

4. Launch Flutter app on Chrome against local API:

  cd frontend/buycott_flutter
  flutter run -d chrome --dart-define=BUYCOTT_API_URL=http://localhost:8000
