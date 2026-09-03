from abc import ABC, abstractmethod

from app.adapters import repository


class AbstractUnitOfWork(ABC):

    # A UoW provides access to the batch repository.
    batches: repository.AbstractRepository

    # When the with block starts, give the code the UoW.
    def __enter__(self):
        return self

    # When the with block finishes, roll back.
    def __exit__(self, *args):
        self.rollback()

    @abstractmethod
    def commit(self):
        raise NotImplementedError

    @abstractmethod
    def rollback(self):
        raise NotImplementedError


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()
        self.batches = repository.SqlAlchemyRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()