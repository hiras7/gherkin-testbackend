
# Backend (Gherkin Intelligence API)

Endpoints:
- `GET /` → banner
- `GET /healthz` → health
- `POST /preview` → JSON with `overviewTotals` (and per-req overview if needed)
- `POST /upload` → generated `.docx` (header: `X-Process-Time`)

Modes (`mode` form field):
- `optimized` (NEW): ≤3 FIT→1 scenario; 4–10 (single theme)→3; >10 or multi-theme→4
- `ultra-optimized`: always 1 scenario (legacy)
- `atomized`: 1 scenario per FIT

Render start command:
```
gunicorn gherkin_backend:app --bind 0.0.0.0:$PORT
```

Env var:
- `FRONTEND_ORIGIN` = your static site origin (e.g., `https://<user>.github.io`). Use `*` for testing.
