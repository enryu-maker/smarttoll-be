from app.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary, DateTime, Boolean
from sqlalchemy.orm import relationship
import uuid


class BookingSlot(Base):
    __tablename__ = 'bookingslot'

    id = Column(Integer, primary_key=True)
    start_time_new = Column(String, nullable=False)
    end_time_new = Column(String, nullable=False)
    bookingcount = Column(Integer, nullable=False)


class Booking(Base):
    __tablename__ = 'booking'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    station_id = Column(Integer, ForeignKey('stations.id'), nullable=False)
    booking_slot = Column(Integer, ForeignKey(
        'bookingslot.id'), nullable=False)
    booking_date = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    order_id = Column(String, unique=True, default=lambda: str(uuid.uuid4()))

    user = relationship("User")
    station = relationship("Station")
