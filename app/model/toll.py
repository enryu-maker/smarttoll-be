from app.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary, DateTime, Boolean
from sqlalchemy.orm import relationship
import datetime


class Camera(Base):
    __tablename__ = 'cameras'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    camera_ip = Column(String, nullable=False, unique=True)
    camera_port = Column(String, nullable=False)
    camera_location = Column(String, nullable=False)
    camera_url = Column(String, nullable=False)


class Toll_Station(Base):
    __tablename__ = 'toll_stations'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    latitude = Column(String, nullable=False)
    longitude = Column(String, nullable=False)
    location = Column(String, nullable=False)
    camera_id = Column(Integer, ForeignKey('cameras.id'))

    camera = relationship('Camera', backref='toll_stations')


class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    number = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
