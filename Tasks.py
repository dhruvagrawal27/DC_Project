from celery import Celery
from PIL import Image, ImageFilter
import base64
import io
import socket

BROKER = 'redis://10.160.65.71:6379/0'
BACKEND = 'redis://10.160.65.71:6379/0'

celery_app = Celery('Tasks', broker=BROKER, backend=BACKEND)

@celery_app.task(name='Tasks.process_image_task')
def process_image_task(encoded_image, filename, process_type, width, height):
    try:
        hostname = socket.gethostname()
        print(f"[{hostname}] Processing {filename} with {process_type}")

        image_data = base64.b64decode(encoded_image)
        img = Image.open(io.BytesIO(image_data))

        if process_type == "grayscale":
            processed = img.convert("L")
        elif process_type == "blur":
            processed = img.filter(ImageFilter.BLUR)
        elif process_type == "resize" and width and height:
            processed = img.resize((int(width), int(height)))
        else:
            processed = img

        buffered = io.BytesIO()
        processed.save(buffered, format="PNG")
        processed_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        safe_filename = f"processed_{hostname}_{filename}"
        return {
            "image_base64": processed_base64,
            "filename": safe_filename
        }

    except Exception as e:
        print("Error during image processing:", str(e))
        raise
