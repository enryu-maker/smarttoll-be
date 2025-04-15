from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, status, Form, UploadFile, File, Query
from sqlalchemy.orm import Session
from app.schemas.user import OTPVerify, LoginRequest, UserResponse, CreateVehicle, VehicleResponse
from app.database import SessionLocale
from app.model.user import User, Vehicle, Wallet, Toll
from app.model.cng import Station
from geopy.distance import geodesic
from datetime import timedelta
from app.service.user_service import generate_otp, send_otp, create_accesss_token, decode_access_token, generate_wallet_number
import base64
router = APIRouter(
    prefix="/v1/user",
    tags=["V1 USER API"],
)


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


db_depandancy = Annotated[Session, Depends(get_db)]
user_dependancy = Annotated[dict, Depends(decode_access_token)]


@router.post('/register/')
async def register_user(
    name: str = Form(...),
    phone_number: str = Form(...),
    db: Session = Depends(get_db)
):

    otp = generate_otp()
    user = User(
        name=name,
        phone_number=phone_number,
        otp=otp
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )

    wallet_number = generate_wallet_number(db)
    wallet = Wallet(
        user_id=user.id,
        balance=0,
        wallet_number=wallet_number
    )

    try:
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create wallet: {str(e)}"
        )

    return {"message": "User Created Sucessfully"}


@router.post("/login/", status_code=status.HTTP_200_OK)
async def login(loginrequest: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.phone_number ==
                                 loginrequest.phone_number).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Please verify your phone number first."
        )

    otp = generate_otp()
    user.otp = otp

    try:
        send_otp(otp=otp, mobile_number=loginrequest.phone_number)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send OTP: {str(e)}"
        )

    db.commit()
    db.refresh(user)

    return {"message": "OTP sent successfully. Please verify to proceed."}


@router.post("/verify/", status_code=status.HTTP_201_CREATED)
async def verify_login(verifyrequest: OTPVerify, db: Session = Depends(get_db)):
    # Retrieve user based on phone number
    user = db.query(User).filter(User.phone_number ==
                                 verifyrequest.phone_number).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if the OTP matches
    if user.otp != verifyrequest.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    # OTP verification successful - activate user and reset OTP
    user.is_active = True
    user.otp = None  # Clear OTP after successful verification
    db.commit()
    db.refresh(user)
    access = create_accesss_token(
        user.name, user.id, timedelta(days=90))

    return {
        "message": "Phone number verified successfully",
        "access_token": access,
    }


@router.get("/profile/", response_model=UserResponse)
async def read_users(user: user_dependancy, db: Session = Depends(get_db)):
    print(user)
    db_user = db.query(User).filter(User.id == user['user_id']).first()
    print(db_user)
    if db_user:
        return db_user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.get("/user-wallet/")
async def read_wallet(user: user_dependancy, db: Session = Depends(get_db)):
    user_wallet = db.query(Wallet).filter(
        Wallet.user_id == user['user_id']).first()
    if user_wallet:
        return user_wallet
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.put("/update-wallet/", status_code=status.HTTP_200_OK)
async def update_wallet(
    user: user_dependancy,
    amount: int,
    db: Session = Depends(get_db)
):
    # Fetch the wallet associated with the user ID
    user_wallet = db.query(Wallet).filter(
        Wallet.user_id == user['user_id']).first()

    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User wallet not found"
        )

    try:
        # Update the wallet balance
        user_wallet.balance = amount + user_wallet.balance
        db.commit()
        db.refresh(user_wallet)  # Optional: Refresh to get the updated data

        return {
            "message": "Wallet updated successfully",
            "wallet_balance": user_wallet.balance
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {e}"
        )


@router.get("/all-wallet-admin/")
async def read_wallet(db: Session = Depends(get_db)):
    # Proper join to avoid repetition
    wallets = db.query(Wallet, User.name).join(
        User, Wallet.user_id == User.id).all()

    if wallets:
        wallet_list = [
            {
                "wallet_id": wallet.id,
                "user_name": name,
                "balance": wallet.balance,
                "user_id": wallet.user_id,
                "wallet_number": wallet.wallet_number
            }
            for wallet, name in wallets
        ]
        return wallet_list

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No wallets found"
    )


@router.put("/update-wallet-admin/", status_code=status.HTTP_200_OK)
async def update_wallet(
    user: int,
    amount: int,
    db: Session = Depends(get_db)
):
    # Fetch the wallet associated with the user ID
    user_wallet = db.query(Wallet).filter(
        Wallet.user_id == user).first()

    print(user_wallet)

    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User wallet not found"
        )

    try:
        # Update the wallet balance
        user_wallet.balance = amount + user_wallet.balance
        db.commit()
        db.refresh(user_wallet)  # Optional: Refresh to get the updated data

        return {
            "message": "Wallet updated successfully",
            "wallet_balance": user_wallet.balance
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {e}"
        )


@router.get("/nearby-station/")
async def nearby_station(
    user_lat: float = Query(..., ge=-90, le=90),  # User's latitude
    user_long: float = Query(..., ge=-180, le=180),  # User's longitude
    range_km: float = Query(5.0, gt=0),
    db: Session = Depends(get_db)
):
    stations = db.query(Station).all()  # Get all stations from the database
    nearby_stations = []

    # Loop through each station and calculate its distance to the user
    for station in stations:
        station_coords = (station.latitude, station.longitude)
        user_coords = (user_lat, user_long)

        # Calculate distance in km
        distance = geodesic(user_coords, station_coords).kilometers

        if distance <= range_km:  # Filter stations within range
            # Convert image to base64 if exists
            if station.image:  # Assuming image is stored as bytes in the Station model
                encoded_image = base64.b64encode(station.image).decode('utf-8')
                station.image = encoded_image

            nearby_stations.append(station)

    if not nearby_stations:
        raise HTTPException(
            status_code=404, detail="No stations found within the specified range")

    return nearby_stations


# api to get tolls
@router.get("/tolls/")
async def get_tolls(user: user_dependancy, db: Session = Depends(get_db)):
    # Fetch tolls associated with the user ID and add the vehicle number based on vehicale id
    user_tolls = db.query(Toll).filter(
        Toll.user_id == user['user_id']).all()
    if user_tolls:
        for toll in user_tolls:
            vehicle = db.query(Vehicle).filter(
                Vehicle.id == toll.vehicle_id).first()
            if vehicle:
                toll.vehicle_number = vehicle.vehicle_number

    if not user_tolls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tolls found"
        )
    return user_tolls


@router.post("/vehicle/")
async def create_vehicle(
    user: user_dependancy,
    vehicle: CreateVehicle,
    db: Session = Depends(get_db)
):
    # Check if the user exists in the database
    db_user = db.query(User).filter(User.id == user['user_id']).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if the vehicle already exists for the user
    existing_vehicle = db.query(Vehicle).filter(
        Vehicle.user_id == user['user_id'],
        Vehicle.vehicle_number == vehicle.vehicle_number
    ).first()

    if existing_vehicle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle is already associated with another user contact Admin"
        )

    # Create a new vehicle associated with the user
    try:
        new_vehicle = Vehicle(
            user_id=user['user_id'],
            vehicle_number=vehicle.vehicle_number,
            vehicle_make=vehicle.vehicle_make,
            vehicle_model=vehicle.vehicle_model,
        )
        db.add(new_vehicle)
        db.commit()
        db.refresh(new_vehicle)
        return {
            "message": "Vehicle created successfully",
            "vehicle_id": new_vehicle.id,
        }
    except Exception as e:
        print(e)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create vehicle: {str(e)}"
        )


@router.get("/vehicle/", response_model=list[VehicleResponse])
async def get_vehicle(
    user: user_dependancy,
    db: Session = Depends(get_db)
):
    # Check if the user exists in the database
    db_user = db.query(User).filter(User.id == user['user_id']).all()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Retrieve the vehicle associated with the user
    db_vehicle = db.query(Vehicle).filter(
        Vehicle.user_id == user['user_id']
    ).all()

    if not db_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )

    return db_vehicle

# get all vehicles with there owner name


@router.get("/all-vehicles")
async def get_all_vehicles(db: Session = Depends(get_db)):
    # Get list of (Vehicle, User.name) tuples
    db_vehicles = db.query(Vehicle, User.name).join(User).all()

    # Manually convert to the response model format
    result = []
    for vehicle, owner_name in db_vehicles:
        result.append(
            {
                "vehicle_id": vehicle.id,
                "vehicle_make": vehicle.vehicle_make,
                "vehicle_model": vehicle.vehicle_model,
                "vehicle_number": vehicle.vehicle_number,
                "owner_name": owner_name

            }
        )
    return result


@router.delete("/vehicle/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db)
):
    # Check if the vehicle exists in the database
    db_vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not db_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )

    # Delete the vehicle
    try:
        db.delete(db_vehicle)
        db.commit()
        return {"message": "Vehicle deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete vehicle: {str(e)}"
        )
