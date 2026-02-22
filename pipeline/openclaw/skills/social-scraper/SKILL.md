# social-scraper

## Purpose
Ingest only public business social metadata from official APIs (no private scraping).

## Command
```bash
/subagents spawn social-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE" --source-snippet "$SOURCE_SNIPPET"
```

## Compliance Rules
- Official API access only (Graph API / business account tokens).
- Skip extraction when credentials are missing.
- Do not ingest private posts, private profiles, or personal PII.
