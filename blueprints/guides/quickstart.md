# Buycott Quickstart

## Prerequisites

- Docker Desktop is running
- Flutter SDK is installed (for frontend)

## 1. Start backend + database

```bash
cd /Users/davidrangelgarcia/Documents/GitHub/buycott-app
docker compose up --build -d
```

## 2. Seed data (required for meaningful search results)

```bash
docker exec buycott-api python /workspace/pipeline/run_full_pipeline.py
```

## 3. Verify backend is healthy

```bash
curl http://localhost:8000/health
```

## 4. Launch Flutter app (Chrome)

```bash
cd frontend/buycott_flutter
flutter pub get
flutter run -d chrome --dart-define=BUYCOTT_API_URL=http://localhost:8000
```

## 5. Optional frontend quality checks

```bash
cd frontend/buycott_flutter
flutter analyze
flutter test
```

## 6. Shut down services

```bash
cd /Users/davidrangelgarcia/Documents/GitHub/buycott-app
docker compose down
```
