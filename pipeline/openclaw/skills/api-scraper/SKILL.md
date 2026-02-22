# api-scraper

## Purpose
Ingest structured JSON/XML menu feeds and business metadata from public APIs.

## Command
```bash
/subagents spawn api-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE" --source-snippet "$SOURCE_SNIPPET"
```

## Output
- `menu_items[]` built from structured fields (`name`, `price`, `description`, `section`)
- evidence `claims[]` with credibility scoring and source traceability
