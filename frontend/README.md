# Buycott Flutter Frontend

Map-first Flutter client implementing:
- permanent map layer
- search overlay with semantic suggestions
- gradient square pins (`minutes away` + `evidence strength`)
- business detail bottom sheet with evidence explanation, capability view, and source transparency
- filters: local-only / show chains / open now / walking distance

## Run

```bash
cd frontend
flutter pub get
flutter run --dart-define=BUYCOTT_API_URL=http://localhost:8000
```
