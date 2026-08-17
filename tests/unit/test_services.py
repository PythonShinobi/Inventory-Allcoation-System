import pytest

from app.domain import model
from app.service_layer import services
from app.adapters import repository


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


class FakeSession:

    committed = False

    def commit(self):
        self.committed = True


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

    repo = FakeRepository([batch])

    result = services.allocate(
        line,
        repo,
        FakeSession(),
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

    repo = FakeRepository([batch])

    with pytest.raises(
        services.InvalidSku,
        match="Invalid sku NONEXISTENTSKU",
    ):
        services.allocate(
            line,
            repo,
            FakeSession(),
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

    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(
        line,
        repo,
        session,
    )

    assert session.committed is True


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

    repo = FakeRepository([batch])

    with pytest.raises(
        model.OutOfStock,
        match="Out of stock for SKU COMPLICATED-LAMP",
    ):
        services.allocate(
            line,
            repo,
            FakeSession(),
        )