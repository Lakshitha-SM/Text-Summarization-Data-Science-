# Render / Railway / Heroku Deployment
# --workers 1   → only one BART model in RAM (critical for free-tier 512 MB)
# --timeout 180 → 3 min allows BART generation + cold model download
# --preload     → loads model before forking workers (faster first request)
web: gunicorn app:app --workers 1 --timeout 180 --bind 0.0.0.0:$PORT --preload
