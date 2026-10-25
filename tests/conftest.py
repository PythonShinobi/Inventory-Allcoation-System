import time
import threading
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from app.domain import model
from app.adapters import orm
from app.adapters.repository import SQLAlchemyProductRepository


@pytest.fixture(scope="session", autouse=True)
def start_mappers():
    orm.start_mappers()

    yield

    clear_mappers()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")

    orm.start_mappers()
    orm.metadata.create_all(engine)

    return sessionmaker(bind=engine)


@pytest.fixture
def session(session_factory):
    return session_factory()

# ---------------------------------------------------------------------------
# Inventory setup
# ---------------------------------------------------------------------------

@pytest.fixture
def add_stock(session):
    """Add products and their batches to the test database."""

    def add_stock_to_database(batches):
        products = {}

        for ref, sku, qty, eta in batches:
            eta = date.fromisoformat(eta) if eta else None

            batch = model.Batch(
                ref=ref,
                sku=sku,
                qty=qty,
                eta=eta
            )

            if sku not in products:
                products[sku] = model.Product(sku, batches=[])

            products[sku].batches.append(batch)

        repository = SQLAlchemyProductRepository(session)

        for product in products.values():
            repository.add(product)

        session.commit()

    return add_stock_to_database

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture
def restart_api():
    """
    Start the Flask API for an end-to-end test and shut it down afterwards.

    The E2E tests communicate with the application through HTTP, so the
    application must be running before the test begins.

    This fixture assumes that ``entrypoints.flask_app`` exposes a Flask
    application object called ``app``.
    """

    from entrypoints.flask_app import app

    server = None

    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 5000, app)

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()

    # Give the server a moment to start listening.
    time.sleep(0.2)

    try:
        yield
    finally:
        server.shutdown()
        thread.join()