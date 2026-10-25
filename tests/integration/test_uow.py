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


def test_uow_can_retrieve_a_product_and_allocate_to_its_batch(
    session_factory,
):
    session = session_factory()

    try:
        # Create the product before its batch.
        session.execute(
            text(
                """
                INSERT INTO products (sku, version_number)
                VALUES (:sku, 0)
                """
            ),
            {"sku": "HIPSTER_WORKBENCH"},
        )

        session.execute(
            text(
                """
                INSERT INTO batches_table
                    (reference, sku, _purchased_quantity, eta)
                VALUES
                    (:reference, :sku, :quantity, :eta)
                """
            ),
            {
                "reference": "batch1",
                "sku": "HIPSTER_WORKBENCH",
                "quantity": 100,
                "eta": None,
            },
        )

        session.commit()
    finally:
        session.close()

    uow = unit_of_work.SQLAlchemyUnitOfWork(session_factory)

    with uow:
        product = uow.products.get("HIPSTER_WORKBENCH")

        assert product is not None

        order_line = model.OrderLine(
            "o1",
            "HIPSTER_WORKBENCH",
            10,
        )

        batch_ref = product.allocate(order_line)

        uow.commit()

    # Verify the allocation persisted in the database.
    verification_session = session_factory()

    try:
        allocated_batch_ref = get_allocated_batch_ref(
            verification_session,
            "o1",
            "HIPSTER_WORKBENCH",
        )

        assert allocated_batch_ref == "batch1"
    finally:
        verification_session.close()
