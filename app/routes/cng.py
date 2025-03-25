from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from app.schemas.cng import cngLogin, workerView, workerRegister, OrderSchema

from app.database import SessionLocale
from app.model.cng import Station, Worker
from app.model.book import Booking
from datetime import timedelta
from app.service.user_service import create_accesss_token, decode_access_token
import requests
import httpx
router = APIRouter(
    prefix="/v1/station",
    tags=["V1 CNG STATION API"],
)


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


db_depandancy = Annotated[Session, Depends(get_db)]
user_dependancy = Annotated[dict, Depends(decode_access_token)]


@router.post("/station-login/", status_code=status.HTTP_200_OK)
async def station_login(loginrequest: cngLogin, db: db_depandancy):
    station = db.query(Station).filter(Station.phone_number ==
                                       loginrequest.phone_number).first()

    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found"
        )

    if station.passcode != loginrequest.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    access = create_accesss_token(
        station.name, station.id, timedelta(days=90))

    return {
        "message": "Login successfully",
        "access_token": access,
    }


@router.put("/toggle-status/", status_code=status.HTTP_201_CREATED)
async def worker_register(user: user_dependancy, db: db_depandancy):
    db_station = db.query(Station).filter(
        Station.id == user["user_id"]).first()

    if not db_station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found"
        )

    # Toggle the is_active status
    # This will switch True to False, and False to True
    db_station.is_active = not db_station.is_active

    db.commit()  # Save the changes to the database

    return db_station.is_active


@router.get("/get-status/", status_code=status.HTTP_200_OK)
async def get_fuel(user: user_dependancy, db: Session = Depends(get_db)):
    # Query the workers from the database by the current user's station_id
    db_station = db.query(Station).filter(
        Station.id == user["user_id"]).first()

    if db_station:
        # Return the list of workers serialized as WorkerRegister Pydantic models
        return db_station.is_active

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Station not found"
    )


@router.put("/toggle-fuel/", status_code=status.HTTP_201_CREATED)
async def worker_register(user: user_dependancy, db: db_depandancy):
    db_station = db.query(Station).filter(
        Station.id == user["user_id"]).first()

    if not db_station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found"
        )

    # Toggle the is_active status
    # This will switch True to False, and False to True
    db_station.fuel_available = not db_station.fuel_available

    db.commit()  # Save the changes to the database

    return db_station.fuel_available


@router.get("/get-fuel/", status_code=status.HTTP_200_OK)
async def get_fuel(user: user_dependancy, db: Session = Depends(get_db)):
    # Query the workers from the database by the current user's station_id
    db_station = db.query(Station).filter(
        Station.id == user["user_id"]).first()

    if db_station:
        # Return the list of workers serialized as WorkerRegister Pydantic models
        return db_station.fuel_available

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Station not found"
    )


@router.get("/get-price/", status_code=status.HTTP_200_OK)
async def get_price(user: user_dependancy, db: Session = Depends(get_db)):
    # Query the workers from the database by the current user's station_id
    db_station = db.query(Station).filter(
        Station.id == user["user_id"]).first()

    if db_station:
        # Return the list of workers serialized as WorkerRegister Pydantic models
        return db_station.price

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Station not found"
    )


@router.get("/get-worker/", response_model=list[workerView], status_code=status.HTTP_200_OK)
async def get_worker(user: user_dependancy, db: Session = Depends(get_db)):
    # Query the workers from the database by the current user's station_id
    db_worker = db.query(Worker).filter(
        Worker.station_id == user["user_id"]).all()

    if db_worker:
        # Return the list of workers serialized as WorkerRegister Pydantic models
        return db_worker

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Station not found"
    )


@router.put("/update-price/", status_code=status.HTTP_201_CREATED)
async def update_price(
    user: user_dependancy,
    amount: str,
    db: db_depandancy
):
    db_station = db.query(Station).filter(
        Station.id == user["user_id"]).first()

    if not db_station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found"
        )

    # Toggle the is_active status
    # This will switch True to False, and False to True
    db_station.price = amount

    db.commit()  # Save the changes to the database

    return db_station.price


@router.post("/worker-login", status_code=status.HTTP_200_OK)
async def worker_login(loginrequest: cngLogin, db: db_depandancy):
    worker = db.query(Worker).filter(Worker.phone_number ==
                                     loginrequest.phone_number).first()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )

    if worker.passcode != loginrequest.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    access = create_accesss_token(
        worker.name, worker.id, timedelta(days=90))

    return {
        "message": "Login successfully",
        "access_token": access,
    }


@router.post("/worker-register/", status_code=status.HTTP_201_CREATED)
async def worker_register(user: user_dependancy, loginrequest: workerRegister, db: db_depandancy):
    station = db.query(Station).filter(Station.id == user['user_id']).first()
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found"
        )
    worker = db.query(Worker).filter(Worker.phone_number ==
                                     loginrequest.phone_number).first()
    if not worker:
        try:
            new_worker = Worker(
                name=loginrequest.name,
                phone_number=loginrequest.phone_number,
                passcode=loginrequest.otp,
                station_id=user['user_id']
            )
            db.add(new_worker)
            db.commit()
            db.refresh(new_worker)
            return {
                "message": "Worker Created successfully",
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{e}"
            )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Worker Already Exist"
    )


# @router.get("/card-fetch/", status_code=status.HTTP_200_OK)
# async def card_fetch(user: user_dependancy, db: Session = Depends(get_db)):
#     worker = db.query(Worker).filter(
#         Worker.id == user['user_id']).all()

#     if not worker:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Worker not found"
#         )

#     resp = requests.get("http://192.168.1.26:8000/read")
#     return resp

@router.get("/card-fetch/", status_code=status.HTTP_200_OK)
async def card_fetch(user: user_dependancy, db: Session = Depends(get_db)):
    # Query the database for the worker
    worker = db.query(Worker).filter(Worker.id == user['user_id']).first()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )

    # Make an external request to the RFID service
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://192.168.2.2:8000/read")
        resp.raise_for_status()  # Check for HTTP error status codes
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error fetching card data from external service"
        )
    user_orders = (
        db.query(Booking)
        .options(
            # Replace with the actual relationship name
            joinedload(Booking.station),
        )
        .filter(Booking.user_id == resp.json()["data"])
        .first()
    )

    print("user order", user_orders.amount)
    print("worker order", worker.station_id)

    if user_orders:
        if user_orders.station.id == worker.station_id:
            if user_orders.status == "Placed":
                response = {
                    "id": user_orders.id,
                    "order_id": user_orders.order_id,
                    "amount": user_orders.amount,
                    "status": user_orders.status,
                    "station": {
                        "id": user_orders.station.id,
                        "name": user_orders.station.name,  # Replace with actual field names
                        "location": user_orders.station.address,
                        "latitude": user_orders.station.latitude,
                        "longitude": user_orders.station.longitude,
                    },
                    "booking_slot": user_orders.booking_slot,
                    "user_id": user_orders.user_id,
                }
                print(resp.json())
                return response
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No order Available"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order not belong to this station"
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Booking Not found"
    )


@router.get("/order-update/", status_code=status.HTTP_200_OK)
async def card_update(
        user: user_dependancy,
        order_id: int,
        db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.id == user['user_id']).first()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )

    try:
        order = (
            db.query(Booking)
            .filter(Booking.user_id == order_id)
            .first()
        )
        order.status = "Completed"
        db.commit()
        db.refresh(order)
        return {
            "message": "Order Completed"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{e}"
        )
