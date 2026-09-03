"""
An integration test checks whether multiple parts of your application 
work correctly together.
"""

from sqlalchemy import text

from app.domain import model
from app.service_layer import unit_of_work


def insert_batch(session, ref, sku, qty, eta):
    session.execute(
        text(
            """
            INSERT INTO batches_table
                (reference, sku, _purchased_quantity, eta)
            VALUES
                (:ref, :sku, :qty, :eta)
            """            
        ), {"ref": ref, "sku": sku, "qty": qty, "eta": eta}
    )


def get_allocated_batch_ref(session, order_id, sku):
    [[order_line_id]] = session.execute(
        text(
            """
            SELECT id
            FROM order_lines_table
            WHERE order_id = :order_id AND sku = :sku
            """        
        ), {"order_id": order_id, "sku": sku}
    )

    [[batch_ref]] = session.execute(
        text(
            """
            SELECT b.reference
            FROM allocations
            JOIN batches_table AS b
                ON allocations.batch_id = b.reference
            WHERE allocations.orderline_id = :orderline_id
            """
        ),
        {"orderline_id": order_line_id}
    )

    return batch_ref


def test_uow_can_retrieve_a_batch_and_allocate_to_it(session_factory):
    session = session_factory()

    insert_batch(
        session,
        "batch1",
        "HIPSTER_WORKBENCH",
        100,
        None
    )

    session.commit()

    uow = unit_of_work.SQLAlchemyUnitOfWork(session_factory)

    with uow:
        batch = uow.batches.get(reference="batch1")

        order_line = model.OrderLine(
            "o1",
            "HIPSTER_WORKBENCH",
            10
        )

        batch.allocate(order_line)

        uow.commit()

        batch_ref = get_allocated_batch_ref(
            session, "o1", "HIPSTER_WORKBENCH"
        )

        assert batch_ref == "batch1"