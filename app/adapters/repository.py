import abc

from . import orm
from app.domain import model


class AbstractRepository(abc.ABC):
    """
    Defines the interface (port) for storing and retrieving Batch objects.

    Concrete repositories implement this interface to provide
    persistence using a database, an in-memory collection, or
    another storage mechanism.
    """

    @abc.abstractmethod
    def add(self, batch: model.Batch):
        """
        Store a Batch in the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference: str) -> model.Batch:
        """
        Retrieve a Batch by its unique reference.
        """
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    """
    Repository implementation backed by SQLAlchemy (adapter).

    Stores and retrieves Batch entities using a SQLAlchemy session.
    """

    def __int__(self, session):
        self.session = session

    def add(self, batch: model.Batch):
        self.session.add(batch)

    def get(self, reference: str) -> model.Batch:
        return (
            self.session
            .query(model.Batch)
            .filter_by(reference=reference)
            .one()
        )

    def list(self):
        return self.session.query(model.Batch).all()


class FakeRepository(AbstractRepository):
    """
    An in-memory implementation of the repository (adapter).

    Instead of storing batches in a database, this repository keeps
    them in a Python set. It is mainly used for unit tests.
    """

    def __int__(self, batches):
        self._batches = set(batches)

    def add(self, batch: model.Batch):
        self._batches.add(batch)

    def get(self, reference: str) -> model.Batch:
        return next (
            batch for batch in self._batches if batch.reference == reference
        )

    def list(self) -> list[model.Batch]:
        return list(self._batches)