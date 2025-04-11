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


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


INDIAN_PLATE_REGEX = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$'


async def detect_number_plate(frame, db: Session):
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Optional: Denoise & enhance contrast
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(gray, 30, 200)

    # Run OCR
    results = reader.readtext(gray)

    for (bbox, text, prob) in results:
        # Clean up the text
        cleaned = text.upper().replace(" ", "").replace("-", "").strip()

        # Match Indian number plate pattern with decent confidence
        if re.match(INDIAN_PLATE_REGEX, cleaned) and prob > 0.7:
            # Offload DB write to background thread
            loop = get_running_loop()
            await loop.run_in_executor(None, partial(add_toll_if_vehicle_exists, cleaned, db))
            return cleaned

    return None


def add_toll_if_vehicle_exists(plate_number: str, db: Session = Depends(get_db)):
    global last_toll_time
    vehicle = db.query(Vehicle).filter(
        Vehicle.vehicle_number == plate_number).first()

    if vehicle:
        # Prevent duplicate toll entries within 5 minutes
        current_time = datetime.datetime.utcnow()
        if plate_number in last_toll_time:
            time_diff = (current_time -
                         last_toll_time[plate_number]).total_seconds()
            if time_diff < 300:  # 300 seconds = 5 minutes
                return {"message": "Toll recently added, skipping."}

        # Insert Toll Entry
        toll_entry = Toll(user_id=vehicle.user_id,
                          vehicle_id=vehicle.id, amount=50)  # Toll amount
        db.add(toll_entry)
        db.commit()

        # deduct amount from wallet
        user_wallet = db.query(Wallet).filter(
            Wallet.user_id == vehicle.user_id).first()
        if user_wallet:
            if user_wallet.balance >= 50:
                user_wallet.balance -= 50
                db.commit()
            else:
                return {"error": "Insufficient balance in wallet"}
        else:
            return {"error": "Wallet not found for user"}
        # Optionally, you can also refresh the wallet to get the updated balance
        db.refresh(user_wallet)

        # Update last toll timestamp
        last_toll_time[plate_number] = current_time
        print(f"Toll added for {plate_number}")  # Debugging
        return {"message": f"Toll added for {plate_number}", "amount": 100}

    return {"error": "Vehicle not registered"}


def video_stream(db: Session):
    # Use the RTSP URL to open the stream
    rtsp_url = "rtsp://admin:123456@206.84.233.93:8001/stream1"
    cap = cv2.VideoCapture(rtsp_url)  # Open RTSP stream
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise ValueError("Failed to open RTSP stream.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect plate automatically
        asyncio.run(detect_number_plate(frame, db))

        # Display detected plate number on the feed
        if plate_number:
            cv2.putText(frame, f"Plate: {plate_number}", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

        # Encode the frame as JPEG
        _, jpeg = cv2.imencode('.jpg', frame)
        frame_bytes = jpeg.tobytes()

        # Yield the frame as an HTTP response (streaming format)
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
        await asyncio.sleep(1)  # Send data every second
        if plate_number:
            await websocket.send_json({"plate_number": plate_number})
