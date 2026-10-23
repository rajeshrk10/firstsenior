#create_engine function from SQLAlchemy to create a database engine
from sqlalchemy import create_engine 

#declarative_base function from SQLAlchemy to create a base class for SQLAlchemy models
from sqlalchemy.ext.declarative import declarative_base

#sessionmaker function from SQLAlchemy to create a session factory for database sessions
from sqlalchemy.orm import sessionmaker

#to read environment variables from a .env file
from dotenv import load_dotenv 
import os

#function to load environment variables from a .env file into the system's environment variables
load_dotenv() 

DATABASE_URL = os.getenv("DATABASE_URL")

# Force psycopg2 driver used to connect to postgresql database with SQLAlchemy. This is necessary because SQLAlchemy defaults to using the asyncpg driver for PostgreSQL, which is not compatible with some features of SQLAlchemy. By replacing the prefix of the DATABASE_URL, we ensure that SQLAlchemy uses the psycopg2 driver instead.`
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Test connection before using it
    pool_recycle=300,        # Recycle connections every 5 minutes
    pool_size=2,             # Keep 2 connections in pool
    max_overflow=1           # Allow 1 extra connections if needed
)

# Create a local session factory for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for SQLAlchemy models
Base = declarative_base()

# function to get a database session. This function is used as a dependency in FastAPI routes to provide a database session for each request. It creates a new session, yields it to the route handler, and ensures that the session is closed after the request is completed.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()