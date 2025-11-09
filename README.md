
# Backend (Gherkin Intelligence API)

Optimized scenario algorithm:
- ≤3 FIT → 1 scenario
- 4–10 FIT (single theme) → 2 scenarios
- >10 FIT or multi‑topic → 3 scenarios

Start (Render):
```
gunicorn gherkin_backend:app --bind 0.0.0.0:$PORT
```
