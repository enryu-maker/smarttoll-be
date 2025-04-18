import cv2
import threading
import time
import re
import numpy as np
from fastapi import APIRouter, Depends, WebSocket
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from ultralytics import YOLO
import easyocr

from app.database import SessionLocale

router = APIRouter()

# Shared variables
latest_frame = None
frame_lock = threading.Lock()
plate_number_global = None

# Initialize YOLO + OCR
model = YOLO("app/routes/best.pt")
reader = easyocr.Reader(['en'])
INDIAN_PLATE_REGEX = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$'


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()

# 🚀 Background thread for detection


def detection_thread():
    global latest_frame, plate_number_global
    while True:
        time.sleep(0.1)  # Tune as needed
        frame_copy = None

        with frame_lock:
            if latest_frame is not None:
                frame_copy = latest_frame.copy()

        if frame_copy is not None:
            try:
                results = model.predict(
                    source=frame_copy, save=False, conf=0.25)
                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        crop = frame_copy[y1:y2, x1:x2]
                        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                        gray = cv2.bilateralFilter(gray, 11, 17, 17)
                        ocr_results = reader.readtext(gray)

                        for (_, text, prob) in ocr_results:
                            cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
                            if re.match(INDIAN_PLATE_REGEX, cleaned) and prob > 0.7:
                                plate_number_global = cleaned
                                print("Detected:", cleaned)
            except Exception as e:
                print("Detection error:", e)


# Start detection thread
threading.Thread(target=detection_thread, daemon=True).start()

# 📹 Video stream


def video_stream():
    global latest_frame
    rtsp_url = "rtsp://206.84.233.93:8001/ch01.264?dev=1"
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise RuntimeError("Failed to open RTSP stream")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Update shared frame
        with frame_lock:
            latest_frame = frame.copy()

        if plate_number_global:
            cv2.putText(frame, f"Plate: {plate_number_global}", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        _, jpeg = cv2.imencode('.jpg', frame)
        frame_bytes = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


@router.get("/live")
async def live_feed():
    return StreamingResponse(video_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

# 🔁 Optional WebSocket


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await asyncio.sleep(1)
        if plate_number_global:
            await websocket.send_json({"plate_number": plate_number_global})
