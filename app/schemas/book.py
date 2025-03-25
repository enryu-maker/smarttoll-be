from pydantic import BaseModel
from datetime import datetime


class BookingSlotCreate(BaseModel):
    start_time: str
    end_time: str
    bookingcount: int


class BookingSlotRead(BookingSlotCreate):
    id: int

    class Config:
        orm_mode = True


class BookingCreate(BaseModel):
    station_id: int
    booking_slot: int
    amount: int
    status: str
    bookDate: str


class BookingRead(BookingCreate):
    order_id: str

    class Config:
        orm_mode = True
