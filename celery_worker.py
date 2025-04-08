# celery_worker.py
from Tasks import celery_app

# Use this to run:  celery -A Tasks.celery_app worker --loglevel=info -Q device1 --pool=solo  
#Redis - & "C:\Program Files\Redis\redis-server.exe" "C:\Program Files\Redis\redis.windows.conf"