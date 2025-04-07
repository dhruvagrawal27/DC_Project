from flask import Flask, request, redirect, url_for, render_template
from celery import Celery
from Tasks import process_image_task
import os
import base64

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config['CELERY_BROKER_URL'] = 'redis://10.160.65.71:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://10.160.65.71:6379/0'

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

@app.route("/upload", methods=["GET", "POST"])
def upload():
    global queue_counter
    if request.method == "POST":
        files = request.files.getlist("images")
        process_type = request.form.get("process_type")
        width = request.form.get("width") or "0"
        height = request.form.get("height") or "0"

        task_ids = []

        for file in files:
            filename = file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            with open(filepath, "rb") as img_file:
                encoded_image = base64.b64encode(img_file.read()).decode()

            target_queue = AVAILABLE_QUEUES[queue_counter % len(AVAILABLE_QUEUES)]
            queue_counter += 1

            task = process_image_task.apply_async(
                args=[encoded_image, filename, process_type, width, height],
                queue=target_queue
            )
            task_ids.append(task.id)

        return redirect(url_for("batch_status", task_ids=",".join(task_ids)))

    return render_template("upload.html")

@app.route("/batch_status/<task_ids>")
def batch_status(task_ids):
    ids = task_ids.split(",")
    results = []

    for task_id in ids:
        result = celery.AsyncResult(task_id)

        if result.ready():
            try:
                result_data = result.get(timeout=10)

                filename = result_data['filename']
                image_base64 = result_data['image_base64']

                result_path = os.path.join(RESULT_FOLDER, filename)
                with open(result_path, 'wb') as f:
                    f.write(base64.b64decode(image_base64))

                results.append({"filename": filename})

            except Exception as e:
                results.append({"error": str(e)})
        else:
            results.append({"processing": True})

    return render_template("results.html", results=results)

@app.route("/")
def home():
    return redirect(url_for("upload"))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
