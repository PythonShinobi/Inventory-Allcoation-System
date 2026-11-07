"""
Unit of Work abstractions for the Inventory Allocation System.

This module defines the Unit of Work pattern used to coordinate
repository access, manage database session lifecycles, and control
transaction boundaries during application operations.

The Unit of Work ensures that related database operations performed
during a business transaction can be committed together or rolled
back if an operation fails.

Classes:
    AbstractUnitOfWork:
        Defines the interface that all Unit of Work implementations
        must follow. Exposes a product repository and declares the
        commit and rollback operations.

    SQLAlchemyUnitOfWork:
        Implements the Unit of Work using SQLAlchemy. Creates and
        manages a database session, provides a repository using that
        session, and handles transaction commits, rollbacks, and
        session cleanup.

    FakeUnitOfWork:
        Provides an in-memory implementation of the Unit of Work
        interface for service-layer testing. Uses a fake repository
        instead of a real database connection.

Database configuration:
    DEFAULT_SESSION_FACTORY:
        Creates SQLAlchemy Session objects using the database engine
        configured through config.get_database_uri().

Responsibilities:
    - Provide a consistent interface for transaction management.
    - Coordinate repository operations through a shared session.
    - Create and manage database sessions.
    - Commit successful business operations.
    - Roll back uncommitted changes when an operation fails.
    - Close database sessions after operations are completed.
    - Provide a fake implementation for isolated service-layer tests.

Transaction lifecycle:
    1. Enter the Unit of Work context.
    2. Create a database session.
    3. Initialise repositories using the shared session.
    4. Perform application and domain operations.
    5. Commit successful changes.
    6. Roll back any remaining uncommitted changes when leaving
       the context.
    7. Close the database session.

Architectural responsibility:
    This module belongs to the application and infrastructure
    boundary. The AbstractUnitOfWork defines the application-facing
    contract, while SQLAlchemyUnitOfWork provides the concrete
    database implementation.

    Application services depend on the abstract Unit of Work rather
    than directly depending on SQLAlchemy. This allows different
    implementations, such as FakeUnitOfWork, to be substituted
    without changing the application service logic.

The Unit of Work coordinates transaction management but does not
implement the inventory allocation business rules. Those rules
belong to the domain model.
"""

from abc import ABC, abstractmethod
from sqlalchemy import create_engine  # Connects the Python application to a database(SQLite, PostgreSQL).
from sqlalchemy.orm import sessionmaker  # Create database sessions.

import config
from app.adapters import repository

# Create the SQLAlchemy session factory which is responsible
# for creating database sessions.
DEFAULT_SESSION_FACTORY = sessionmaker(
    bind=create_engine(config.get_database_uri())
)

class AbstractUnitOfWork(ABC):
    # Type Annotation:
    # Any Unit of Work implementation should expose a products attribute 
    # that behaves like an AbstractProductRepository.
    products: repository.AbstractProductRepository

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.rollback()

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        """Does not undo a transaction that has already been committed. 
        The committed data remains saved."""
        raise NotImplementedError


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """Manage database transactions using SQLAlchemy."""

    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    def __enter__(self):
        # A database session is created. This session manages the interaction with 
        # the database and provides the transactional context for the operations performed 
        # through it.
        self.session = self.session_factory()

        # A repository is created using that same session. This is important because the repository and Unit 
        # of Work now share the same database session.
        self.products = repository.SQLAlchemyProductRepository(self.session)
        
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        if hasattr(self, "session"):
            self.session.rollback()


class FakeUnitOfWork(AbstractUnitOfWork):
    """In-memory Unit of Work for service-layer tests."""

    def __init__(self, products=()):
        self.products = repository.FakeRepository(products)
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass