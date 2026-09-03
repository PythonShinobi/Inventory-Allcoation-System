from datetime import date
from sqlalchemy import text

from app.domain import model
from app.adapters import repository


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
            WHERE order_id=:order_id
            AND sku=:sku
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
            INSERT INTO batches_table (reference, sku, _purchased_quantity, eta)
            VALUES (:reference, 'GENERIC-SOFA', 100, NULL)
            """
        ),
        {"reference": reference},
    )

    [[batch_id]] = session.execute(
        text(
            """
            SELECT reference
            FROM batches_table
            WHERE reference=:reference
            """
        ),
        {"reference": reference},
    )

    return batch_id


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


def test_repository_can_save_a_batch(session):
    batch = model.Batch("batch1", "RUSTY-SOAPDISH", 100, eta=None)

    repo = repository.SqlAlchemyRepository(session)

    repo.add(batch)

    session.commit()

    rows = list(
        session.execute(
            text(
                """
                SELECT reference, sku, _purchased_quantity, eta
                FROM batches_table
                """
            )
        )
    )

    assert rows == [
        ("batch1", "RUSTY-SOAPDISH", 100, None)
    ]


def test_repository_can_retrieve_a_batch_with_allocations(session):
    orderline_id = insert_order_line(session)

    batch1_id = insert_batch(session, "batch1")
    insert_batch(session, "batch2")

    insert_allocation(
        session,
        orderline_id,
        batch1_id,
    )

    repo = repository.SqlAlchemyRepository(session)

    retrieved = repo.get("batch1")

    expected = model.Batch(
        "batch1",
        "GENERIC-SOFA",
        100,
        eta=None,
    )

    assert retrieved == expected
    assert retrieved.sku == expected.sku
    assert retrieved._purchased_quantity == expected._purchased_quantity

    assert retrieved._allocations == {
        model.OrderLine("order1", "GENERIC-SOFA", 12)
    }