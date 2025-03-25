from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, UploadFile, File
from sqlalchemy.orm import Session
from app.schemas.cng import cngLogin, workerView, workerRegister
from app.database import SessionLocale
from app.model.cng import Station, Worker
from datetime import timedelta
from app.service.user_service import create_accesss_token, decode_access_token

router = APIRouter(
    prefix="/v1/helper",
    tags=["V1 CNG STATION HELPER API"],
)
