# === Tasks.py ===
from celery import Celery
from PIL import Image, ImageFilter
import base64
import io
import socket
import zlib
import redis

BROKER = 'redis://10.160.68.133:6379/0'
BACKEND = 'redis://10.160.68.133:6379/0'
r = redis.Redis(host='10.160.68.133', port=6379)

celery_app = Celery('Tasks', broker=BROKER, backend=BACKEND)

def generate_crc32(data):
    return zlib.crc32(data.encode()) & 0xffffffff

@celery_app.task(name='Tasks.process_image_task')
def process_image_task(encoded_image, filename, process_type, width, height, job_id):
    try:
        hostname = socket.gethostname()
        print(f"[{hostname}] Processing {filename} with {process_type}")

        image_data = base64.b64decode(encoded_image)
        img = Image.open(io.BytesIO(image_data))

        if process_type == "grayscale":
            processed = img.convert("L")
        elif process_type == "blur":
            processed = img.filter(ImageFilter.BLUR)
        elif process_type == "resize" and width and height and width != "0" and height != "0":
            processed = img.resize((int(width), int(height)))
        else:
            processed = img

        buffered = io.BytesIO()
        processed.save(buffered, format="PNG")
        processed_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Store CRC for processed image
        r.set(f"crc:{job_id}", generate_crc32(processed_base64))

        safe_filename = f"processed_{hostname}_{filename}"
        return {
            "image_base64": processed_base64,
            "filename": safe_filename
        }

    except Exception as e:
        print("Error during image processing:", str(e))
        raise