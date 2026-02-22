# html-scraper

## Purpose
Extract menu and business claims from static HTML pages.

## Command
```bash
/subagents spawn html-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE" --source-snippet "$SOURCE_SNIPPET"
```

## Output
- `claims[]` with source snippet traceability
- `menu_items[]` with section/name/description/price/dietary tags

## Reliability
- 429/5xx calls are retried with exponential backoff.
- Claims are scored for extraction confidence and source credibility.
