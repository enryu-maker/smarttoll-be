import cv2
import easyocr
import re
import asyncio
import datetime
import numpy as np
from functools import partial
from asyncio import get_running_loop
from fastapi import APIRouter, WebSocket, Depends
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session

from ultralytics import YOLO

from app.model.user import Vehicle, Toll, Wallet, UnauthorizedVehicle
from app.database import SessionLocale

router = APIRouter()
reader = easyocr.Reader(['en'])
plate_number_global = None  # For WebSocket broadcast
last_toll_time = {}

# Load custom YOLOv8 model
model = YOLO("app/routes/best.pt")

INDIAN_PLATE_REGEX = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$'


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


def detect_number_plate(frame: np.ndarray) -> str:
    global plate_number_global
    results = model.predict(source=frame, save=False, conf=0.25)
    # print(results)

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            crop = frame[y1:y2, x1:x2]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            gray = cv2.bilateralFilter(gray, 11, 17, 17)
            ocr_results = reader.readtext(gray)

            for (_, text, prob) in ocr_results:
                cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
                print(cleaned, prob)
                if re.match(INDIAN_PLATE_REGEX, cleaned) and prob > 0.7:
                    plate_number_global = cleaned
                    print(f"Detected plate: {cleaned}")
                    return cleaned

    plate_number_global = None
    return None


def process_plate_number(plate_number: str,  db: Session = Depends(get_db)):
    global last_toll_time
    print("i was here")
    vehicle = db.query(Vehicle).filter(
        Vehicle.vehicle_number == plate_number).first()

    if vehicle:

        current_time = datetime.datetime.utcnow()
        if plate_number in last_toll_time:
            time_diff = (current_time -
                         last_toll_time[plate_number]).total_seconds()
            if time_diff < 300:
                return

        toll_entry = Toll(user_id=vehicle.user_id,
                          vehicle_id=vehicle.id, amount=50)
        db.add(toll_entry)

        wallet = db.query(Wallet).filter(
            Wallet.user_id == vehicle.user_id).first()
        if wallet:
            if wallet.balance >= 50:
                wallet.balance -= 50
            else:
                return
        else:
            return

        db.commit()
        db.refresh(wallet)
        last_toll_time[plate_number] = current_time
        print(f"Toll added for {plate_number}")

    else:
        existing = db.query(UnauthorizedVehicle).filter(
            UnauthorizedVehicle.vehicle_number == plate_number).first()
        if not existing:
            entry = UnauthorizedVehicle(vehicle_number=plate_number)
            db.add(entry)
            db.commit()
            db.refresh(entry)
            print(f"Unauthorized vehicle detected: {plate_number}")


def video_stream(db: Session = Depends(get_db)):
    rtsp_url = "rtsp://admin:123456@206.84.233.93:8001/stream1"
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise RuntimeError("Failed to open RTSP stream")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        try:
            plate_number = detect_number_plate(frame)
            if plate_number:
                process_plate_number(plate_number, db)
                cv2.putText(frame, f"Plate: {plate_number}", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        except Exception as e:
            print(f"Detection error: {e}")

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
        if plate_number_global:
            await websocket.send_json({"plate_number": plate_number_global})


@router.get("/unauthorized-vehicles")
async def get_unauthorized_vehicles(db: Session = Depends(get_db)):
    return db.query(UnauthorizedVehicle).all()
