# ocr-scraper

## Purpose
Extract text/menu hints from image-based menus and signage.

## Command
```bash
/subagents spawn ocr-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE" --source-snippet "$SOURCE_SNIPPET"
```

## Extraction Stack
- Primary OCR: Tesseract (`pytesseract`)
- Optional fallback: Vision endpoint (`OPENCLAW_VISION_ENDPOINT`)

## Output
- OCR-backed `claims[]`
- `menu_items[]` when price/item patterns are detected
