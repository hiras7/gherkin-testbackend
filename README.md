
# Backend (Gherkin Intelligence API) – v3

Endpoints
- `GET /` — banner
- `GET /healthz` — health probe
- `POST /preview` — JSON with `overviewTotals` and rules
- `POST /upload` — generated Gherkin `.docx`
- `POST /generate_playwright` — generated Playwright `.spec.ts`

Modes (`mode` form field)
- **optimized**: ≤3 FIT→1, 4–10 (single theme)→2, >10 or multi‑topic→3 scenarios
- **atomized**: 1 scenario per FIT
- **ultra-optimized**: always 1 scenario

Start (Render)
```
gunicorn gherkin_backend:app --bind 0.0.0.0:$PORT
```
