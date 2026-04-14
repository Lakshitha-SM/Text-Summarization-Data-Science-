# Render / Railway Deployment
# gunicorn is the production WSGI server for Python web apps.
# The app object is defined in app.py as `app`.
web: gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT
