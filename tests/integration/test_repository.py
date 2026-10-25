
"""
Integration tests for the SQLAlchemy Product repository.

An integration test checks whether multiple parts of the
application work correctly together.
"""

from sqlalchemy import text

from app.domain import model
from app.adapters import repository


def insert_product(session, sku):
    session.execute(
        text(
            """
            INSERT INTO products (sku, version_number)
            VALUES (:sku, 0)
            """
        ),
        {"sku": sku},
    )


def insert_order_line(session):
    session.execute(
        text(
            """
            INSERT INTO order_lines_table (order_id, sku, qty)
            VALUES ('order1', 'GENERIC-SOFA', 12)
            """
        )
    )

    [[orderline_id]] = session.execute(
        text(
            """
            SELECT id
            FROM order_lines_table
            WHERE order_id = :order_id
            AND sku = :sku
            """
        ),
        {
            "order_id": "order1",
            "sku": "GENERIC-SOFA",
        },
    )

    return orderline_id


def insert_batch(session, reference):
    session.execute(
        text(
            """
            INSERT INTO batches_table
                (reference, sku, _purchased_quantity, eta)
            VALUES
                (:reference, 'GENERIC-SOFA', 100, NULL)
            """
        ),
        {"reference": reference},
    )

    return reference


def insert_allocation(session, orderline_id, batch_id):
    session.execute(
        text(
            """
            INSERT INTO allocations (orderline_id, batch_id)
            VALUES (:orderline_id, :batch_id)
            """
        ),
        {
            "orderline_id": orderline_id,
            "batch_id": batch_id,
        },
    )


def test_repository_can_save_a_product_with_a_batch(session):
    batch = model.Batch(
        "batch1",
        "RUSTY-SOAPDISH",
        100,
        eta=None,
    )

    product = model.Product(
        "RUSTY-SOAPDISH",
        batches=[batch],
    )

    repo = repository.SQLAlchemyProductRepository(session)

    repo.add(product)
    session.commit()

    product_rows = list(
        session.execute(
            text(
                """
                SELECT sku, version_number
                FROM products
                """
            )
        )
    )

    batch_rows = list(
        session.execute(
            text(
                """
                SELECT reference, sku, _purchased_quantity, eta
                FROM batches_table
                """
            )
        )
    )

    assert product_rows == [("RUSTY-SOAPDISH", 0)]
    assert batch_rows == [
        ("batch1", "RUSTY-SOAPDISH", 100, None)
    ]


def test_repository_can_retrieve_a_product_with_batch_allocations(
    session,
):
    insert_product(session, "GENERIC-SOFA")

    orderline_id = insert_order_line(session)

    batch1_id = insert_batch(session, "batch1")
    insert_batch(session, "batch2")

    insert_allocation(
        session,
        orderline_id,
        batch1_id,
    )

    session.commit()

    repo = repository.SQLAlchemyProductRepository(session)

    retrieved = repo.get("GENERIC-SOFA")

    assert retrieved is not None
    assert retrieved.sku == "GENERIC-SOFA"
    assert len(retrieved.batches) == 2

    batch1 = next(
        batch
        for batch in retrieved.batches
        if batch.reference == "batch1"
    )

    expected = model.Batch(
        "batch1",
        "GENERIC-SOFA",
        100,
        eta=None,
    )

    assert batch1 == expected
    assert batch1.sku == expected.sku
    assert (
        batch1._purchased_quantity
        == expected._purchased_quantity
    )

    assert batch1._allocations == {
        model.OrderLine("order1", "GENERIC-SOFA", 12)
    }
