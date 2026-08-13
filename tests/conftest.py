"""Shared pytest fixtures: per-test SQLite bound to the shared SQLAlchemy Base."""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Default env before any engine import in other modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("VERIAGENT_AUTO_INIT_DB", "1")
os.environ.setdefault("VERIFLEET_SKIP_LLM", "1")
os.environ.setdefault("VERIFLEET_QUEUE_DISPATCH", "0")
os.environ.pop("PUBSUB_TOPIC", None)
os.environ.pop("VERIFLEET_PUBSUB_PUSH", None)


@pytest.fixture()
def db_session():
    """
    Isolated in-memory SQLite with ALL mapped tables created on the real Base
    used by production models (no importlib reload).
    """
    from core_engine.db.database import Base
    import core_engine.db.models  # noqa: F401
    import core_engine.db.fleet_models  # noqa: F401
    import core_engine.control_plane.models  # noqa: F401
    import core_engine.auth.models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def sample_invoice_input():
    from datetime import date
    from shared.schemas import Address, Customer, InvoiceInput, InvoiceLine, TaxLine

    return InvoiceInput(
        series="T",
        number="1",
        issue_date=date.today(),
        issuer_tax_id="B12345674",
        customer=Customer(
            tax_id="A11111119",
            name="Cliente SA",
            address=Address(street="C/1", city="Madrid", postal_code="28001"),
        ),
        lines=[
            InvoiceLine(
                description="Servicio", quantity=1, unit_price=100.0, total_amount=100.0
            )
        ],
        taxes=[TaxLine(tax_rate=21.0, base_amount=100.0, tax_amount=21.0)],
        total_base=100.0,
        total_tax=21.0,
        total_amount=121.0,
    )
