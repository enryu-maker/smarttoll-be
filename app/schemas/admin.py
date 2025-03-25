from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class AdminLogin(BaseModel):
    email: str = Field(...)
    password: str = Field(...)


class AdminRegister(BaseModel):
    name: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)
