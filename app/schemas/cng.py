from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import base64


class cngLogin(BaseModel):
    phone_number: str = Field(..., max_length=10)
    otp: Optional[str] = None


class workerRegister(BaseModel):
    name: str
    phone_number: str = Field(..., max_length=10)
    otp: Optional[str]

    class Config:
        orm_mode = True


class workerView(BaseModel):
    name: str
    phone_number: str = Field(..., max_length=10)
    passcode: Optional[str]

    class Config:
        orm_mode = True


class StationSchema(BaseModel):
    id: int
    name: str
    price: str
    fuel_available: bool
    phone_number: str
    image: Optional[str] = None

    class Config:
        orm_mode = True


class OrderSchema(BaseModel):
    id: int
    user_id: int
    station_id: int
    status: str

    class Config:
        orm_mode = True
