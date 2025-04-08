# === heartbeat.py (run separately on each worker) ===
import redis
import socket
import time

r = redis.Redis(host='10.160.68.133', port=6379)
worker_id = socket.gethostname()

while True:
    r.set(f"heartbeat:{worker_id}", "alive", ex=90)  # expires in 90s
    time.sleep(30)