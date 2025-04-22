import os
import cv2
import threading
import time
import re
import uuid
import shutil
import numpy as np
import torch
import asyncio
from queue import Queue
from fastapi import APIRouter, WebSocket
from starlette.responses import StreamingResponse
from ultralytics import YOLO
import easyocr

router = APIRouter()

# Create folders if they don't exist
os.makedirs("detected_plates", exist_ok=True)

# Shared variables
latest_frame = None
frame_lock = threading.Lock()
plate_number_global = None
frame_queue = Queue(maxsize=10)

# Load YOLO model and EasyOCR with GPU support if available
model = YOLO("app/routes/best.pt")
if torch.cuda.is_available():
    model.to("cuda")
    reader = easyocr.Reader(['en'], gpu=True)
else:
    reader = easyocr.Reader(['en'], gpu=False)

INDIAN_PLATE_REGEX = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$'


def save_frame_to_memory(frame):
    if not frame_queue.full():
        frame_queue.put(frame)


def detection_thread():
    global plate_number_global
    while True:
        time.sleep(0.1)  # Slight delay to avoid CPU overload
        if frame_queue.empty():
            continue

        try:
            frame = frame_queue.get()
            results = model.predict(source=frame, save=False, conf=0.25)
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    crop = frame[y1:y2, x1:x2]
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    gray = cv2.bilateralFilter(gray, 11, 17, 17)
                    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                 cv2.THRESH_BINARY, 11, 2)
                    ocr_results = reader.readtext(
                        gray, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

                    for (_, text, prob) in ocr_results:
                        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
                        if re.match(INDIAN_PLATE_REGEX, cleaned) and prob > 0.7:
                            plate_number_global = cleaned
                            print("Detected:", cleaned)
                            filename = f"detected_plates/{cleaned}_{uuid.uuid4().hex}.jpg"
                            cv2.imwrite(filename, frame)
        except Exception as e:
            print("Detection error:", e)


threading.Thread(target=detection_thread, daemon=True).start()


def video_stream():
    global latest_frame
    rtsp_url = "rtsp://206.84.233.93:8001/ch01.264?dev=1"
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise RuntimeError("Failed to open RTSP stream")

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame_count += 1
        if frame_count % 3 == 0:  # Process every 3rd frame
            save_frame_to_memory(frame)

        with frame_lock:
            latest_frame = frame.copy()

        display_frame = frame.copy()
        if plate_number_global:
            cv2.putText(display_frame, f"Plate: {plate_number_global}", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        _, jpeg = cv2.imencode('.jpg', display_frame)
        frame_bytes = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


@router.get("/live")
async def live_feed():
    return StreamingResponse(video_stream(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await asyncio.sleep(1)
        if plate_number_global:
            await websocket.send_json({"plate_number": plate_number_global})
