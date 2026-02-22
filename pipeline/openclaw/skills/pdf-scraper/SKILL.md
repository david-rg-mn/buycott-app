# pdf-scraper

## Purpose
Extract menu text and claims from PDF menus/documents.

## Command
```bash
/subagents spawn pdf-scraper --source-url "$SOURCE_URL" --source-type "$SOURCE_TYPE" --source-snippet "$SOURCE_SNIPPET"
```

## Extraction Stack
- Primary: `PyMuPDF`
- Secondary: `pdfplumber`
- Fallback OCR: Tesseract on rendered PDF pages

## Output
- `menu_items[]`
- `claims[]`
- extraction metadata includes parser method used
