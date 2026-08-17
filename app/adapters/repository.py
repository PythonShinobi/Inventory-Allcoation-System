"""
Repository abstractions and implementations for the inventory system.

This module defines the repository port used by the application and
the adapters that implement that port.

A repository provides an abstraction over persistence. The service
layer should be able to retrieve and store domain objects without
knowing whether those objects are stored in SQLAlchemy, an in-memory
collection, or another persistence mechanism.

Architecture::

    Service Layer
          |
          v
    AbstractRepository
          ^
          |
       ┌──┴──────────────────┐
       |                     |
       v                     v
    SqlAlchemyRepository   FakeRepository
       |                     |
       v                     v
    Database             Python memory

``AbstractRepository`` is the port.

``SqlAlchemyRepository`` is an adapter that connects the application
to a SQLAlchemy-backed database.

``FakeRepository`` is an adapter that stores objects in memory and is
primarily useful for unit testing the service layer.

The important architectural idea is that the service layer depends on
the abstraction rather than on a specific persistence technology.

For example, the service layer can declare::

    def allocate(
        line: model.OrderLine,
        repo: AbstractRepository,
        session,
    ):
        ...

The service does not need to know whether ``repo`` is a
``SqlAlchemyRepository`` or ``FakeRepository``.

Production example::

    session = get_session()
    repo = SqlAlchemyRepository(session)

    services.allocate(line, repo, session)

Testing example::

    batch = model.Batch(
        ref="batch-001",
        sku="LAMP-001",
        qty=100,
        eta=None,
    )

    repo = FakeRepository([batch])

    services.allocate(line, repo, FakeSession())

This allows service-layer tests to run without a real database.

Responsibilities::

    - Define the repository interface.
    - Provide persistence adapters.
    - Hide storage details from the service layer.
    - Allow different persistence implementations to be substituted.

Non-responsibilities::

    - Defining inventory business rules.
    - Deciding which batch should be allocated.
    - Handling HTTP requests.
    - Returning JSON responses.
    - Coordinating application use cases.

The domain model remains independent of this module. Repository
implementations translate persistence operations into interactions
with domain objects.
"""

from abc import ABC, abstractmethod

from app.domain import model


class AbstractRepository(ABC):
    """
    Defines the repository port for storing and retrieving Batch objects.

    This is an abstraction used by the service layer. It describes
    what the application needs from a repository without specifying
    how the data is actually stored.

    Concrete adapters implement this interface.

    Implementations may use:

        - A relational database.
        - SQLAlchemy.
        - An in-memory collection.
        - Another persistence mechanism.

    Example::

        def allocate(line, repo: AbstractRepository, session):
            batches = repo.list()
            ...
    """

    @abstractmethod
    def add(self, batch: model.Batch):
        """
        Store a Batch in the repository.

        Args:
            batch: The domain Batch entity to store.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, reference: str) -> model.Batch:
        """
        Retrieve a Batch by its unique reference.

        Args:
            reference: The unique reference identifying the batch.

        Returns:
            The corresponding Batch domain object.
        """
        raise NotImplementedError

    @abstractmethod
    def list(self) -> list[model.Batch]:
        """
        Return all batches available through the repository.

        Returns:
            A list of Batch domain objects.
        """
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    """
    SQLAlchemy implementation of the repository port.

    This class is an adapter between the application and SQLAlchemy.

    The service layer depends on ``AbstractRepository`` rather than
    directly depending on this class. This keeps SQLAlchemy-specific
    persistence details out of the service layer.

    Example::

        session = get_session()
        repo = SqlAlchemyRepository(session)

        batch = repo.get("batch-001")

    Attributes:
        session: SQLAlchemy session used to communicate with the
            database.
    """

    def __init__(self, session):
        self.session = session

    def add(self, batch: model.Batch):
        """
        Add a Batch to the SQLAlchemy session.

        The change is not necessarily committed immediately.
        Transaction management is handled by the application layer
        or Unit of Work.
        """

        self.session.add(batch)

    def get(self, reference: str) -> model.Batch:
        """
        Retrieve a Batch from the database by its reference.

        Args:
            reference: Unique batch reference.

        Returns:
            The matching Batch.

        Raises:
            SQLAlchemy exception:
                If no matching batch exists or multiple matches exist.
        """

        return (
            self.session
            .query(model.Batch)
            .filter_by(reference=reference)
            .one()
        )

    def list(self) -> list[model.Batch]:
        """
        Retrieve all batches from the database.

        Returns:
            A list of Batch objects.
        """

        return self.session.query(model.Batch).all()


class FakeRepository(AbstractRepository):
    """
    In-memory implementation of the repository port.

    FakeRepository is primarily used for unit testing.

    Instead of communicating with a database, it stores Batch objects
    in a Python set. This allows the service layer to be tested without
    SQLAlchemy or a real database.

    Example::

        batch = model.Batch(
            ref="batch-001",
            sku="LAMP-001",
            qty=100,
            eta=None,
        )

        repo = FakeRepository([batch])

        result = repo.get("batch-001")

    This class implements the same ``AbstractRepository`` interface
    as ``SqlAlchemyRepository``, which allows either implementation
    to be passed to the service layer.
    """

    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch: model.Batch):
        """
        Add a Batch to the in-memory collection.

        Args:
            batch: The Batch entity to store.
        """

        self._batches.add(batch)

    def get(self, reference: str) -> model.Batch:
        """
        Retrieve a Batch from the in-memory collection.

        Args:
            reference: Unique batch reference.

        Returns:
            The matching Batch.

        Raises:
            StopIteration:
                If no batch with the requested reference exists.
        """

        return next(
            batch
            for batch in self._batches
            if batch.reference == reference
        )

    def list(self) -> list[model.Batch]:
        """
        Return all batches stored in memory.

        Returns:
            A list of Batch objects.
        """

        return list(self._batches)