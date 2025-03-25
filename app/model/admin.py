from app.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary, DateTime, Boolean


class Admin(Base):
    __tablename__ = 'admin'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
