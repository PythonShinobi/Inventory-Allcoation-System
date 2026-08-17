import time
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from app.adapters import orm
from app.domain import model
from app.adapters.repository import SqlAlchemyRepository


@pytest.fixture(scope="session", autouse=True)
def start_mappers():
    orm.start_mappers()

    yield

    clear_mappers()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

@pytest.fixture
def session():
    """
    Provide a fresh SQLAlchemy session backed by an in-memory SQLite database.
    """

    engine = create_engine("sqlite:///:memory:")

    orm.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)

    with Session() as session:
        yield session


# ---------------------------------------------------------------------------
# Inventory setup
# ---------------------------------------------------------------------------

@pytest.fixture
def add_stock(session):
    """
    Add batches to the test database.

    The E2E tests use this fixture to create the inventory needed for
    an allocation scenario.

    Example:

        add_stock([
            ("batch-1", "SKU-1", 100, "2011-01-01"),
            ("batch-2", "SKU-1", 50, None),
        ])
    """

    def add_stock_to_database(batches):
        repository = SqlAlchemyRepository(session)

        for reference, sku, quantity, eta in batches:
            batch = model.Batch(
                ref=reference,
                sku=sku,
                qty=quantity,
                eta=eta,
            )

            repository.add(batch)

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