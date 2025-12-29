import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL from environment
POSTGRES_USER = os.getenv("POSTGRES_USER", "veriagent")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "securepassword")
POSTGRES_DB = os.getenv("POSTGRES_DB", "veriagent_core")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

# Use SQLite for testing if host is not set or specifically for E2E if desired
# But per prompt, we use Postgres style
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
