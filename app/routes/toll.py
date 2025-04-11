from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocale
from app.model.toll import Camera, Toll_Station
from datetime import timedelta
from app.service.user_service import create_accesss_token, decode_access_token
import requests
import httpx
router = APIRouter(
    prefix="/v1/toll",
    tags=["V1 TOLL STATION API"],
)


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


db_depandancy = Annotated[Session, Depends(get_db)]
user_dependancy = Annotated[dict, Depends(decode_access_token)]


@router.get('/get-camera/')
async def get_camera(
    db: Session = Depends(get_db)
):
    camera = db.query(Camera).all()
    return camera


@router.post('/add-camera/')
async def add_camera(
    name: str = Form(...),
    camera_ip: str = Form(...),
    camera_location: str = Form(...),
    camera_port: str = Form(...),
    camera_url: str = Form(...),
    db: Session = Depends(get_db)
):
    camera = Camera(
        name=name,
        camera_ip=camera_ip,
        camera_location=camera_location,
        camera_port=camera_port,
        camera_url=camera_url
    )

    try:
        db.add(camera)
        db.commit()
        db.refresh(camera)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add camera: {str(e)}"
        )

    return camera


@router.get('/get-toll-station/')
async def get_toll_station(
    db: Session = Depends(get_db)
):
    toll_station = db.query(Toll_Station).options(
        joinedload(Toll_Station.camera)).all()
    return toll_station


@router.post('/add-toll-station/')
async def add_toll_station(
    name: str = Form(...),
    latitude: str = Form(...),
    longitude: str = Form(...),
    location: str = Form(...),
    camera_id: int = Form(...),
    db: Session = Depends(get_db)
):
    toll_station = Toll_Station(
        name=name,
        latitude=latitude,
        longitude=longitude,
        location=location,
        camera_id=camera_id
    )

    try:
        db.add(toll_station)
        db.commit()
        db.refresh(toll_station)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add toll station: {str(e)}"
        )

    return toll_station
