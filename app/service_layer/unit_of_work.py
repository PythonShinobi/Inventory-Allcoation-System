"""Unit of Work abstractions for application transactions."""

from abc import ABC, abstractmethod

from app.adapters import repository


class AbstractUnitOfWork(ABC):
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
        raise NotImplementedError


class FakeUnitOfWork(AbstractUnitOfWork):
    """In-memory Unit of Work for service-layer tests."""

    def __init__(self, products=()):
        self.products = repository.FakeRepository(products)
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass