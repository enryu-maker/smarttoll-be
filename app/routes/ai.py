import cv2
import easyocr
import re
import asyncio
from asyncio import get_running_loop
from functools import partial
import datetime
import numpy as np
from fastapi import APIRouter, WebSocket, Depends
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.model.user import Vehicle, Toll, Wallet
from app.database import SessionLocale

router = APIRouter()
reader = easyocr.Reader(['en'])  # English OCR

# Database dependency


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


# Regex for Indian number plates
INDIAN_PLATE_REGEX = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$'

# Detect number plate from frame


async def detect_number_plate(frame, db: Session):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    results = reader.readtext(gray)

    for (bbox, text, prob) in results:
        cleaned = text.upper().replace(" ", "").replace("-", "").strip()
        if re.match(INDIAN_PLATE_REGEX, cleaned) and prob > 0.7:
            loop = get_running_loop()
            await loop.run_in_executor(None, partial(add_toll_if_vehicle_exists, cleaned, db))
            return cleaned
    return None

# Add toll if vehicle exists


def add_toll_if_vehicle_exists(plate_number: str, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(
        Vehicle.vehicle_number == plate_number).first()
    if vehicle:
        current_time = datetime.datetime.utcnow()
        last_entry = db.query(Toll).filter(
            Toll.vehicle_id == vehicle.id
        ).order_by(Toll.created_at.desc()).first()

        if last_entry and (current_time - last_entry.created_at).total_seconds() < 300:
            return  # Skip if toll was added in the last 5 minutes

        toll_entry = Toll(user_id=vehicle.user_id,
                          vehicle_id=vehicle.id, amount=50)
        db.add(toll_entry)

        user_wallet = db.query(Wallet).filter(
            Wallet.user_id == vehicle.user_id).first()
        if user_wallet:
            if user_wallet.balance >= 50:
                user_wallet.balance -= 50
            else:
                return  # Insufficient balance
        else:
            return  # Wallet not found

        db.commit()
        db.refresh(user_wallet)
        print(f"Toll added for {plate_number}")

# Streaming the video feed


def video_stream(db: Session):
    cap = cv2.VideoCapture(0)  # Use webcam or RTSP stream
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise ValueError("Failed to open camera stream.")

    plate_number_local = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        plate_number_local = asyncio.run(detect_number_plate(frame, db))

        if plate_number_local:
            cv2.putText(frame, f"Plate: {plate_number_local}", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

        _, jpeg = cv2.imencode('.jpg', frame)
        frame_bytes = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


@router.get("/live")
async def live_feed(db: Session = Depends(get_db)):
    return StreamingResponse(video_stream(db), media_type="multipart/x-mixed-replace; boundary=frame")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await asyncio.sleep(1)
        # WebSocket can be expanded to share plate updates if needed
        await websocket.send_json({"message": "WebSocket active"})
