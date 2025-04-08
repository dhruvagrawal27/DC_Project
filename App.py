# === app.py ===
from flask import Flask, request, redirect, url_for, render_template, jsonify
from celery import Celery
from Tasks import process_image_task, generate_crc32
import os
import base64
import uuid
import redis

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config['CELERY_BROKER_URL'] = 'redis://10.160.68.133:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://10.160.68.133:6379/0'

r = redis.Redis(host='10.160.68.133', port=6379)

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )
    celery.conf.update(app.config)
    return celery

celery = make_celery(app)

AVAILABLE_QUEUES = ['device1', 'device2']
queue_counter = 0

job_db = {}

@app.route("/upload", methods=["GET", "POST"])
def upload():
    global queue_counter
    if request.method == "POST":
        files = request.files.getlist("images")
        process_type = request.form.get("process_type")
        width = request.form.get("width") or "0"
        height = request.form.get("height") or "0"

        job_ids = []

        if not files or files[0].filename == "":
            return "No images selected. Please try again.", 400

        for file in files:
            filename = file.filename
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(filepath)

            with open(filepath, "rb") as img_file:
                encoded_image = base64.b64encode(img_file.read()).decode()

            crc = generate_crc32(encoded_image)

            target_queue = AVAILABLE_QUEUES[queue_counter % len(AVAILABLE_QUEUES)]
            queue_counter += 1

            job_id = str(uuid.uuid4())
            job_ids.append(job_id)
            job_db[job_id] = {
                "job_id": job_id,
                "status": "processing",
                "assigned_worker": target_queue,
                "filename": unique_filename,
                "result_url": None
            }

            r.set(f"crc:{job_id}", crc)

            process_image_task.apply_async(
                args=[encoded_image, unique_filename, process_type, width, height, job_id],
                queue=target_queue,
                task_id=job_id
            )

        return redirect(url_for("batch_status", task_ids=",".join(job_ids)))
    return render_template("upload.html")

@app.route("/batch_status/<task_ids>")
def batch_status(task_ids):
    ids = task_ids.split(",")
    results = []

    for job_id in ids:
        result = celery.AsyncResult(job_id)
        if result.ready():
            try:
                result_data = result.get(timeout=10)
                filename = result_data['filename']
                image_base64 = result_data['image_base64']

                # Validate CRC
                original_crc = int(r.get(f"crc:{job_id}"))
                current_crc = generate_crc32(image_base64)
                if original_crc != current_crc:
                    raise ValueError("CRC mismatch. Data integrity error.")

                result_path = os.path.join(RESULT_FOLDER, filename)
                with open(result_path, 'wb') as f:
                    f.write(base64.b64decode(image_base64))

                job_db[job_id]["status"] = "done"
                job_db[job_id]["result_url"] = f"/{result_path}"
                results.append({"filename": filename})
            except Exception as e:
                job_db[job_id]["status"] = "error"
                results.append({"error": str(e)})
        else:
            results.append({"processing": True})
    return render_template("results.html", results=results)

@app.route("/jobs")
def jobs_api():
    return jsonify(job_db)

@app.route("/")
def home():
    return redirect(url_for("upload"))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

