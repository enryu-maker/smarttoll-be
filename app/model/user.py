from app.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary, DateTime, Boolean
from sqlalchemy.orm import relationship
import datetime


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    icon = Column(LargeBinary, nullable=True)
    name = Column(String)
    phone_number = Column(String(10), nullable=False, unique=True)
    otp = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)


class Vehicle(Base):
    __tablename__ = 'vehicles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    vehicle_number = Column(String(50), nullable=False, unique=True)
    vehicle_make = Column(String(50), nullable=False)
    vehicle_model = Column(String(50), nullable=False)

    user = relationship('User', backref='vehicles')


class UnauthorizedVehicle(Base):
    __tablename__ = 'unauthorizedvehicles'
    id = Column(Integer, primary_key=True)
    vehicle_number = Column(String(50), nullable=False, unique=True)


class Wallet(Base):
    __tablename__ = 'wallets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    balance = Column(Integer, nullable=False, default=0)
    wallet_number = Column(String(50), nullable=False, unique=True)

    user = relationship('User', backref='wallets')


class Toll(Base):
    __tablename__ = 'tolls'
    id = Column(Integer, primary_key=True)
    time = Column(
        String, default=lambda: datetime.utcnow().strftime('%H:%M:%S'))
    user_id = Column(Integer, ForeignKey('users.id'))
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'))
    amount = Column(Integer, nullable=False)

    user = relationship('User', backref='tolls')
    vehicle = relationship('Vehicle', backref='tolls')
