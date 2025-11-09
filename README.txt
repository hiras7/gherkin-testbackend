
# Gherkin Backend Deployment

## Files
- gherkin_backend.py
- requirements.txt
- uploads/
- outputs/

## Render Deployment
Start Command:
    gunicorn gherkin_backend:app --bind 0.0.0.0:$PORT

## Local Run
pip install -r requirements.txt
python gherkin_backend.py
