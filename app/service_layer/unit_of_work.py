"""Unit of Work abstractions for application transactions."""

from abc import ABC, abstractmethod
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from app.adapters import repository


# Create the SQLAlchemy session factory.
DEFAULT_SESSION_FACTORY = sessionmaker(
    bind=create_engine(config.get_postgres_uri())
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
        self.session = self.session_factory()
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