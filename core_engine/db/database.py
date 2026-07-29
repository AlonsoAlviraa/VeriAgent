import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

POSTGRES_USER = os.getenv("POSTGRES_USER", "veriagent")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "securepassword")
POSTGRES_DB = os.getenv("POSTGRES_DB", "veriagent_core")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")

# Prefer explicit DATABASE_URL; sqlite for local/tests when set
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}",
)

_connect_args = {}
_engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    _engine_kwargs = {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(drop: bool = False):
    """Create all ORM tables (used by tests and sqlite bootstrap)."""
    # Import models so metadata is populated
    from core_engine.db import models  # noqa: F401
    from core_engine.control_plane import models as cp_models  # noqa: F401
    from core_engine.auth import models as auth_models  # noqa: F401

    if drop:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
