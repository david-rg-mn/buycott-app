# spa-scraper

## Purpose
Render JavaScript-heavy pages with Playwright and extract structured menu claims.

## Command
```bash
/subagents spawn spa-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE" --source-snippet "$SOURCE_SNIPPET"
```

## Runtime
- Uses Playwright Chromium (`networkidle` wait).
- Falls back to HTML parser if rendering fails.

## Output
- Same schema as `html-scraper` plus render metadata (`render_ratio`, fallback indicators).
