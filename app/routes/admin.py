from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, status, Form, UploadFile, File
from sqlalchemy.orm import Session
from app.schemas.admin import AdminLogin, AdminRegister
from app.schemas import user as userSchema
from app.schemas import book as bookSchema
from app.database import SessionLocale
from app.model.admin import Admin
from app.model import user, cng, book

from datetime import timedelta
from app.service.user_service import create_accesss_token, decode_access_token, hash_pass, verify_user

router = APIRouter(
    prefix="/v1/admin",
    tags=["V1 ADMIN API"],
)


def get_db():
    db = SessionLocale()
    try:
        yield db
    finally:
        db.close()


db_depandancy = Annotated[Session, Depends(get_db)]
user_dependancy = Annotated[dict, Depends(decode_access_token)]


@router.post("/admin-register", status_code=status.HTTP_201_CREATED)
async def admin_register(loginrequest: AdminRegister, db: db_depandancy):

    admin = db.query(Admin).filter(Admin.email ==
                                   loginrequest.email).first()
    if not admin:
        try:
            new_admin = Admin(
                name=loginrequest.name,
                email=loginrequest.email,
                password=hash_pass(loginrequest.password),
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            return {
                "message": "Admin Created successfully",
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{e}"
            )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Admin Already Exist"
    )


@router.post("/admin-login", status_code=status.HTTP_200_OK)
async def worker_login(loginrequest: AdminLogin, db: db_depandancy):
    admin = verify_user(loginrequest=loginrequest, db=db, Model=Admin)

    if admin:
        access = create_accesss_token(
            admin.name, admin.id, timedelta(days=90))

        return {
            "message": "Login successfully",
            "access_token": access,
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Error in Admin Login"
    )

# Add Station


@router.get("/slots/", status_code=status.HTTP_200_OK)
async def get_slots(db: db_depandancy):
    try:
        # Query all the booking slots from the database
        slots = db.query(book.BookingSlot).all()

        if not slots:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No slots found"
            )

        # Prepare a list of slots to return
        slot_list = [{
            "id": slot.id,
            "start_time": slot.start_time_new,
            "end_time": slot.end_time_new,
            "time":  slot.start_time_new + "-" + slot.end_time_new,
            "bookingcount": slot.bookingcount
        } for slot in slots]

        return {
            "message": "Slots retrieved successfully",
            "slots": slot_list
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error retrieving slots: {e}"
        )


@router.post("/slot/", status_code=status.HTTP_201_CREATED)
async def create_slot(bookslotschema: bookSchema.BookingSlotCreate, db: db_depandancy):
    try:
        new_slot = book.BookingSlot(
            start_time_new=bookslotschema.start_time,
            end_time_new=bookslotschema.end_time,
            bookingcount=bookslotschema.bookingcount
        )
        db.add(new_slot)
        db.commit()
        db.refresh(new_slot)
        return {
            "message": "Slot Added Sucessfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{e}"
        )


@router.delete("/slot/{slot_id}", status_code=status.HTTP_201_CREATED)
async def create_slot(slot_id: int, db: db_depandancy):
    db_user = db.query(book.BookingSlot).filter(
        book.BookingSlot.id == slot_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found")


@router.post("/station-register", status_code=status.HTTP_201_CREATED)
async def station_register(
    # user: user_dependancy,
    name: str = Form(...),
    image: UploadFile = File(None),
    phone_number: str = Form(...),
    passcode: str = Form(...),
    description: str = Form(None),
    latitude: str = Form(...),
    longitude: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    country: str = Form(...),
    postal_code: str = Form(...),
    fuel_available: bool = Form(True),
    price: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = True
    if admin:
        icon_data = await image.read() if image else None

        new_station = cng.Station(
            name=name,
            image=icon_data,
            phone_number=phone_number,
            passcode=passcode,
            description=description,
            latitude=latitude,
            longitude=longitude,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            fuel_available=fuel_available,
            price=price,
            is_active=True
        )
        try:
            db.add(new_station)
            db.commit()
            db.refresh(new_station)

            return {
                "message": "Station created successfully",
            }

        except Exception as e:
            print(e)
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# User API


@router.get("/get-users/", response_model=list[userSchema.UserResponse])
async def read_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(user.User).offset(skip).limit(limit).all()


@router.delete("/delete-users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(user.User).filter(user.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found")
