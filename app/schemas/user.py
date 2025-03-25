from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import base64


class UserBase(BaseModel):
    name: str
    email: str
    password: str
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True


class OTPVerify(BaseModel):
    phone_number: str
    otp: int


class LoginRequest(BaseModel):
    email: str
    password: str

# Schema for creating a vehicle


class CreateVehicle(BaseModel):
    vehicle_number: str
    vehicle_make: str
    vehicle_model: str

    class Config:
        orm_mode = True  # Enables ORM compatibility for SQLAlchemy models


# Schema for displaying a vehicle (e.g., as a response model)
class VehicleResponse(BaseModel):
    id: int
    user_id: int
    vehicle_number: str
    vehicle_make: str
    vehicle_model: str

    class Config:
        orm_mode = True
