web: gunicorn --log-level info --timeout 60 --workers 2 --worker-class sync --max-requests 100 --max-requests-jitter 20 app:app
worker: python sync_knack_to_supabase.py 