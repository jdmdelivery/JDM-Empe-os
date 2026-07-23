web: flask db upgrade && python scripts/create_superadmin.py && gunicorn "run:app" --bind 0.0.0.0:$PORT --workers 2 --timeout 120
