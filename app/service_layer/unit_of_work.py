"""
Unit of Work abstractions for managing application transactions.

This module defines the Unit of Work interface and its SQLAlchemy
implementation. A Unit of Work provides access to repositories and
defines the transaction boundary for an application operation.

The abstract Unit of Work specifies the operations required to commit
or roll back changes without depending on a particular persistence
technology. The SQLAlchemy implementation creates a database session,
provides a SQLAlchemy repository through the ``batches`` attribute,
and manages the session lifecycle.

The application service layer depends on the abstract Unit of Work,
while the concrete SQLAlchemy implementation is responsible for
connecting those abstractions to the database.
"""

from abc import ABC, abstractmethod

from app.adapters import repository


class AbstractUnitOfWork(ABC):
    """
    Abstract interface for a Unit of Work.

    A Unit of Work provides access to the repositories needed by an
    application operation and defines the transaction boundary for that
    operation.

    Attributes:
        batches:
            Repository used to access and modify Batch objects.
            Concrete Unit of Work implementations provide the actual
            repository implementation.
    """

    batches: repository.AbstractRepository

    def __enter__(self):
        """
        Enter the Unit of Work context.

        Returns:
            The current Unit of Work instance.
        """

        return self

    def __exit__(self, *args):
        """
        Roll back the current transaction when leaving the context.

        Concrete implementations may perform additional cleanup after
        the transaction is rolled back.
        """

        self.rollback()

    @abstractmethod
    def commit(self):
        """
        Commit the current transaction.

        Concrete implementations must define how changes are permanently
        persisted.
        """

        raise NotImplementedError

    @abstractmethod
    def rollback(self):
        """
        Roll back the current transaction.

        Concrete implementations must define how uncommitted changes
        are discarded.
        """

        raise NotImplementedError


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    SQLAlchemy implementation of the Unit of Work.

    This implementation creates a SQLAlchemy session for the duration of
    a Unit of Work and provides a SQLAlchemy repository for accessing
    Batch objects.

    Args:
        session_factory:
            Callable that creates a new SQLAlchemy database session.
    """

    def __init__(self, session_factory):
        """
        Initialize the Unit of Work.

        Args:
            session_factory:
                Callable used to create a new database session when the
                Unit of Work is entered.
        """

        self.session_factory = session_factory

    def __enter__(self):
        """
        Start the Unit of Work.

        Creates a new SQLAlchemy session and uses it to create the
        repository exposed through the ``batches`` attribute.

        Returns:
            The active Unit of Work instance.
        """

        self.session = self.session_factory()

        self.batches = repository.SqlAlchemyRepository(self.session)

        return super().__enter__()

    def __exit__(self, *args):
        """
        End the Unit of Work.

        Rolls back any uncommitted changes and closes the database
        session.
        """

        super().__exit__(*args)

        self.session.close()

    def commit(self):
        """
        Commit the current database transaction.
        """
        
        self.session.commit()

    def rollback(self):
        """
        Roll back the current database transaction.
        """
        
        self.session.rollback()