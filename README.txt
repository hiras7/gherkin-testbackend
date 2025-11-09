
# Gherkin Backend Deployment

This bundle contains a Flask backend for generating Gherkin scenarios from .docx requirement documents.

## Files
- gherkin_backend.py: Main backend application
- requirements.txt: Python dependencies
- uploads/: Folder for uploaded files
- outputs/: Folder for generated output files

## Deployment on Render
1. Create a new Web Service on [Render](https://render.com).
2. Upload this ZIP bundle or push to a GitHub repo.
3. Set the Start Command to:
   gunicorn gherkin_backend:app --bind 0.0.0.0:$PORT
4. Add environment variable:
   FRONTEND_ORIGIN=* (or your frontend URL)

## Local Development
pip install -r requirements.txt
python gherkin_backend.py

Access the service at http://localhost:5000
