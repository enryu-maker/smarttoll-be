import cv2
import easyocr
import asyncio
import datetime
import numpy as np
from fastapi import APIRouter, WebSocket, Depends
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.model.user import Vehicle, Toll, Wallet
from app.database import SessionLocale

router = APIRouter()
reader = easyocr.Reader(['en'])  # English OCR
plate_number = None  # Store detected plate number globally
last_toll_time = {}  # Dictionary to store last toll entry timestamp per vehicle


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


async def detect_number_plate(frame, db: Session = Depends(get_db)):
    global plate_number
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # OCR to detect text in the frame
    plates = reader.readtext(gray)

    for (bbox, text, prob) in plates:
        if prob > 0.5:  # Confidence threshold
            plate_number = text.strip().replace(" ", "")  # Clean the plate number
            # Add toll if vehicle is found
            add_toll_if_vehicle_exists(plate_number, db)
            return text  # Return extracted number plate

    plate_number = None
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
    cap = cv2.VideoCapture(0)  # Open webcam

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
        await asyncio.sleep(1)  # Send data every second
        if plate_number:
            await websocket.send_json({"plate_number": plate_number})
