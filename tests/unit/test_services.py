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


class FakeRepository(repository.AbstractProductRepository):
    def __init__(self, products=()):
        self._products = {product.sku: product for product in products}

    def add(self, product):
        self._products[product.sku] = product

    def get(self, sku):
        return self._products.get(sku)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.products = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_returns_allocation():
    line = model.OrderLine("oref", "COMPLICATED-LAMP", 10)

    batch = model.Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    product = model.Product("COMPLICATED-LAMP", [batch])

    uow = FakeUnitOfWork()
    uow.products.add(product)

    result = services.allocate(line, uow)

    assert result == "b1"


def test_error_for_invalid_sku():
    line = model.OrderLine("o1", "NONEXISTENTSKU", 10)

    uow = FakeUnitOfWork()

    with pytest.raises(
        services.InvalidSku,
        match="Invalid sku NONEXISTENTSKU",
    ):
        services.allocate(line, uow)


def test_commits():
    line = model.OrderLine("o1", "OMINOUS-MIRROR", 10)

    batch = model.Batch("b1", "OMINOUS-MIRROR", 100, eta=None)
    product = model.Product("OMINOUS-MIRROR", [batch])

    uow = FakeUnitOfWork()
    uow.products.add(product)

    services.allocate(line, uow)

    assert uow.committed is True


def test_error_for_out_of_stock():
    line = model.OrderLine("o1", "COMPLICATED-LAMP", 200)

    batch = model.Batch("b1", "COMPLICATED-LAMP", 100, eta=None)
    product = model.Product("COMPLICATED-LAMP", [batch])

    uow = FakeUnitOfWork()
    uow.products.add(product)

    with pytest.raises(
        model.OutOfStock,
        match="COMPLICATED-LAMP",
    ):
        services.allocate(line, uow)