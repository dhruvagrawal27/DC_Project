# celery_worker.py
from Tasks import celery_app

# Use this to run: `celery -A celery_worker.celery_app worker --loglevel=info`
