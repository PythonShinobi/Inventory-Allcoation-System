"""
Unit tests for the application service layer.

A unit test tests one small piece of a program in isolation.

These tests use fake implementations of the repository and Unit of Work
so that the service layer can be tested without connecting to a database.
"""

import pytest

from app.domain import model
from app.adapters import repository
from app.service_layer import services, unit_of_work


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(
            b for b in self._batches
            if b.reference == reference
        )

    def list(self):
        return list(self._batches)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_returns_allocation():
    line = model.OrderLine(
        "o1",
        "COMPLICATED-LAMP",
        10,
    )

    batch = model.Batch(
        "b1",
        "COMPLICATED-LAMP",
        100,
        eta=None,
    )

    uow = FakeUnitOfWork()
    uow.batches = FakeRepository([batch])

    result = services.allocate(
        line,
        uow,
    )

    assert result == "b1"


def test_error_for_invalid_sku():
    line = model.OrderLine(
        "o1",
        "NONEXISTENTSKU",
        10,
    )

    batch = model.Batch(
        "b1",
        "AREALSKU",
        100,
        eta=None,
    )

    uow = FakeUnitOfWork()
    uow.batches = FakeRepository([batch])

    with pytest.raises(
        services.InvalidSku,
        match="Invalid sku NONEXISTENTSKU",
    ):
        services.allocate(
            line,
            uow,
        )


def test_commits():
    line = model.OrderLine(
        "o1",
        "OMINOUS-MIRROR",
        10,
    )

    batch = model.Batch(
        "b1",
        "OMINOUS-MIRROR",
        100,
        eta=None,
    )

    uow = FakeUnitOfWork()
    uow.batches = FakeRepository([batch])

    services.allocate(
        line,
        uow,
    )

    assert uow.committed is True


def test_error_for_out_of_stock():
    line = model.OrderLine(
        "o1",
        "COMPLICATED-LAMP",
        200,
    )

    batch = model.Batch(
        "b1",
        "COMPLICATED-LAMP",
        100,
        eta=None,
    )

    uow = FakeUnitOfWork()
    uow.batches = FakeRepository([batch])

    with pytest.raises(
        model.OutOfStock,
        match="Out of stock for SKU COMPLICATED-LAMP",
    ):
        services.allocate(
            line,
            uow,
        )
