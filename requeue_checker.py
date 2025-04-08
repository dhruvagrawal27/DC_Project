import redis
import json
import time

r = redis.Redis(host='10.160.68.133', port=6379)

registered_workers = [b'device1', b'device2']

while True:
    time.sleep(60)
    active_workers = [key.decode().split(":")[1] for key in r.scan_iter("heartbeat:*")]
    for worker in registered_workers:
        if worker.decode() not in active_workers:
            for key in r.scan_iter("crc:*"):
                job_id = key.decode().split(":")[1]
                job_data = r.hget("jobs", job_id)
                if job_data:
                    job_info = json.loads(job_data)
                    if job_info['status'] != 'done':
                        job_info['status'] = 'pending'
                        job_info['assigned_worker'] = None
                        with r.pipeline() as pipe:
                            pipe.multi()
                            pipe.hset("jobs", job_id, json.dumps(job_info))
                            pipe.lpush("job_queue", job_id)
                            pipe.execute()
