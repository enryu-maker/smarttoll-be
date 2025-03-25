from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# PROD_URL = "postgresql://cngstation_user:OpINFXni1oT9BInwGTmvyhnKlMetBqjQ@dpg-cspql72j1k6c739ppm7g-a.oregon-postgres.render.com/cngstation"
SQL_DATABASE_URL = "sqlite:///./smartoll.db"
PSQL_DATABASE_URL = "postgresql://postgres:123456@localhost/smartcng"
engine = create_engine(SQL_DATABASE_URL)

SessionLocale = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
