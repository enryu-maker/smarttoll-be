from app.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary, DateTime, Boolean
from sqlalchemy.orm import relationship
import datetime


class Station(Base):
    __tablename__ = 'stations'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    # Consider storing image paths/URLs if images are large
    image = Column(LargeBinary, nullable=True)
    phone_number = Column(String(10), nullable=False, unique=True)
    passcode = Column(String(4), nullable=False)
    description = Column(String, nullable=True)
    latitude = Column(String, nullable=False)
    longitude = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)
    fuel_available = Column(Boolean, default=False)  # Corrected typo
    price = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    # Pluralized the `backref` name
    workers = relationship('Worker', backref='station')


class Worker(Base):
    __tablename__ = 'worker'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone_number = Column(String(10), nullable=False, unique=True)
    passcode = Column(String(4), nullable=False)
    station_id = Column(Integer, ForeignKey('stations.id'))
