# Lock Zone AI Floor Plan Analyzer

AI-powered floor plan analysis and quote generation.

## Live App
https://lockzone-ai-floorplan.onrender.com

## API Endpoints

### `POST /api/analyze`
Upload a floor plan PDF, select automation systems and tier, and receive summary metrics along with download links for an annotated floor plan and quote PDF.

### `GET /api/data`
Returns the current automation catalog, tiers, and pricing data that power the analyzer.

### `POST /api/data`
Submit a JSON object to extend or override automation types, tiers, and pricing. Incoming payloads are merged with safe defaults, so customisations persist without blocking future updates.

## Analysis Enhancements
- Sequential PDF page rendering with pdf2image/PyMuPDF fallbacks for large documents.
- Advanced contour, OCR, and line-segmentation pipelines to detect rooms, text, labels, and structural lines before placing automation points.

## Updating the automation data

Automation symbols, pricing, and tier multipliers live in `data/automation_data.json`. To teach the app new categories or pricing:

1. Fetch the existing configuration with `GET /api/data`.
2. Merge your updates locally (add symbols, change prices, introduce tiers, etc.).
3. POST the revised JSON back to `/api/data`.

The server deep-merges your payload with the built-in defaults, so repository updates won't overwrite your training data. If you want those settings to persist in source control, commit the updated `data/automation_data.json` file.
