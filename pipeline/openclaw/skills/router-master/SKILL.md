# router-master

## Purpose
Master router for Phase 5 OpenClaw ingestion. Detects source modality with heuristic scoring and dispatches specialized sub-agents through `sessions.spawn` / `/subagents spawn`.

## Inputs
- `business_id` (required)
- `source_url` (required)
- `source_type` (required)
- `source_snippet` (optional)

## Routing Protocol
1. Probe URL headers/content.
2. Score modalities: `html`, `spa`, `pdf`, `image`, `api`, `social`.
3. Spawn top modality plus close-confidence alternates.
4. Persist route evidence (`scores`, `reasons`, `spawn_modalities`) for auditability.

## Spawn Examples
```bash
/subagents spawn html-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE"
/subagents spawn spa-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE"
/subagents spawn pdf-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE"
/subagents spawn ocr-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE"
/subagents spawn api-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE"
/subagents spawn social-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE"
```

## Sandbox Rule
- Must run inside Docker sandbox unless explicit override is set (`--allow-host-execution`).
