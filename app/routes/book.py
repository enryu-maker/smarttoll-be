from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, status, Form, UploadFile, File
from sqlalchemy.orm import Session
from app.schemas.book import BookingRead
from app.schemas import book as bookSchema
from app.database import SessionLocale
from app.model.book import Booking, BookingSlot
from app.model.user import User, Wallet
from app.model.cng import Station
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
from datetime import timedelta
from app.service.user_service import create_accesss_token, decode_access_token, hash_pass, verify_user

router = APIRouter(
    prefix="/v1/order",
    tags=["V1 ORDER API"],
)


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


db_depandancy = Annotated[Session, Depends(get_db)]
user_dependancy = Annotated[dict, Depends(decode_access_token)]


@router.post("/create/", status_code=status.HTTP_200_OK)
async def create_order(user: user_dependancy, bookingcreate: bookSchema.BookingCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.id == user['user_id']).first()
        user_wallet = db.query(Wallet).filter(
            Wallet.user_id == user['user_id']).first()

        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if not user_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User wallet not found"
            )

        if user_wallet.balance < bookingcreate.amount:
            return {"message": "Insufficient wallet balance"}

        new_order = Booking(
            user_id=db_user.id,
            station_id=bookingcreate.station_id,
            booking_slot=bookingcreate.booking_slot,
            amount=bookingcreate.amount,
            status=bookingcreate.status,
            booking_date=bookingcreate.bookDate
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        new_balance = user_wallet.balance - bookingcreate.amount
        user_wallet.balance = new_balance
        db.commit()
        db.refresh(user_wallet)

        return {
            "message": "Order created successfully",
            "order_id": new_order.id
        }

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/station-orders/", response_model=list[dict], status_code=status.HTTP_200_OK)
async def station_order(user: user_dependancy, db: Session = Depends(get_db)):

    orders = db.query(
        Booking.order_id,
        User.name.label('user_name'),  # Alias the user name
        Station.name.label('station_name'),  # Alias the station name
        BookingSlot.start_time_new,
        BookingSlot.end_time_new,
        Booking.amount,
        Booking.status
    ).join(
        User, User.id == Booking.user_id  # Join with User to get the username
    ).join(
        # Join with Station to get the station name
        Station, Station.id == Booking.station_id
    ).join(
        # Join with BookingSlot for the start_time_new
        BookingSlot, BookingSlot.id == Booking.booking_slot
    ).filter(
        # Filter by the station_id of the current user
        Booking.station_id == user['user_id']
    ).all()

    if orders:
        # Format the data to include the user_name, station_name, and other fields
        result = []
        for order in orders:
            result.append({
                "order_id": order.order_id,
                "user_name": order.user_name,  # Access the aliased user_name
                "station_name": order.station_name,  # Access the aliased station_name
                # Access the start_time_new field from BookingSlot
                "slot_start_time": order.start_time_new,
                "slot_end_time": order.end_time_new,
                "amount": order.amount,
                "status": order.status
            })
        return result

    # If no orders found, raise an HTTP 404 exception
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Booking Not Found"
    )


@router.get("/station-total-income/", response_model=dict, status_code=status.HTTP_200_OK)
async def get_total_income(user: user_dependancy, db: Session = Depends(get_db)):
    # Query the total income for the station by summing the amount field in Booking
    total_income = db.query(func.sum(Booking.amount)).join(
        Station, Station.id == Booking.station_id
    ).filter(
        Booking.station_id == user['user_id']
    ).scalar()

    if total_income is not None:
        return {
            "total_income": total_income
        }

    # If no income found, return zero or handle it as needed
    return {
        "total_income": 0
    }


@router.get("/user-orders/", status_code=status.HTTP_200_OK)
async def user_order(user: user_dependancy, db: Session = Depends(get_db)):
    user_orders = (
        db.query(Booking)
        .options(
            # Replace with the actual relationship name
            joinedload(Booking.station),
        )
        .filter(Booking.user_id == user['user_id'])
        .all()
    )

    if user_orders:
        # Format the response to include details from related tables
        response = [
            {
                "id": order.id,
                "order_id": order.order_id,
                "amount": order.amount,
                "status": order.status,
                "station": {
                    "id": order.station.id,
                    "name": order.station.name,  # Replace with actual field names
                    "location": order.station.address,
                    "latitude": order.station.latitude,
                    "longitude": order.station.longitude,
                },
                "booking_slot": order.booking_slot,
                "user_id": order.user_id,
            }
            for order in user_orders
        ]
        return response

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Booking Not found"
    )
