
# Gherkin Backend — Deployment Package

This package provides a Flask backend that parses requirement `.docx` files and generates optimized Gherkin scenarios.

## Endpoints
- `GET /` — service banner
- `GET /healthz` — health probe
- `POST /preview` — returns JSON preview (parsed requirements, rules, overview)
- `POST /upload` — returns generated `.docx` (sets header `X-Process-Time`)

## Local Development
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python gherkin_backend.py
# open http://localhost:5000
```

### Quick test
```bash
curl -i http://localhost:5000/
# Preview
curl -i -X POST -F "file=@/path/to/sample.docx" http://localhost:5000/preview
# Generate
curl -o gherkin_output.docx -X POST -F "file=@/path/to/sample.docx" http://localhost:5000/upload
```

## Render Deployment
1. **Create Web Service** on Render and connect this repo or upload these files.
2. **Build command**: (auto) `pip install -r requirements.txt`
3. **Start command**:
   ```
   gunicorn gherkin_backend:app --bind 0.0.0.0:$PORT
   ```
4. **Environment variable**:
   - `FRONTEND_ORIGIN` — your frontend origin (e.g., `https://<user>.github.io`). Use `*` while testing.

### Health check (optional)
Set health check path to `/healthz`.

## Frontend Hookup
Open your static site with:
```
?api=https://<your-app>.onrender.com
```
Or paste the URL in the frontend Settings dialog. Then **Preview** and **Generate** should work.
