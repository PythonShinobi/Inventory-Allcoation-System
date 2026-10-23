"""
Application service layer for the inventory allocation system.

This module contains application-level use cases that coordinate
the domain model with application infrastructure through a Unit of Work.

The service layer is responsible for orchestration. It retrieves the
current state of the application through the Unit of Work, performs
application-level validation, delegates business decisions to the
domain model, and commits successful changes.

It does not contain the core inventory business rules. Those rules
belong in ``app.domain.model``. It also does not handle HTTP, JSON,
or Flask-specific concerns.

Architecture::

    API / Flask
        |
        v
    Service Layer
        |
        v
    Abstract Unit of Work
        |
        +------> Repository
        |
        +------> Database Session
        |
        v
    Result

Typical flow::

    allocate()
        |
        +-- uow.batches.list()
        |
        +-- is_valid_sku()
        |
        +-- model.allocate()
        |
        +-- uow.commit()
        |
        +-- return batch reference

The service layer depends on ``AbstractUnitOfWork`` rather than on a
specific database session or repository implementation. This keeps
the service layer independent of the persistence technology and makes
the use cases easier to test.

Exceptions:

    InvalidSku:
        Raised when the requested SKU does not exist in the current
        inventory state.

    model.OutOfStock:
        Raised by the domain model when no batch can satisfy the
        requested order line.

See Also:

    app.domain.model:
        Contains the domain entities and core inventory allocation rules.

    app.service_layer.unit_of_work:
        Defines the Unit of Work abstraction used by this service layer.

    app.adapters.repository:
        Contains repository implementations used by the Unit of Work.
"""

from datetime import date
from typing import Optional

from app.domain import model
from app.service_layer import unit_of_work


class InvalidSku(Exception):
    """
    Raised when an order contains a SKU that does not exist.

    This is an application-level validation error. The service layer
    checks the current inventory state before invoking the domain
    allocation logic.
    """

    pass


def is_valid_sku(sku, batches) -> bool:
    """
    Return True if the SKU exists in the available batches.

    Args:
        sku:
            The SKU to validate.

        batches:
            An iterable of Batch objects representing current inventory.

    Returns:
        True if at least one batch contains the requested SKU;
        otherwise False.
    """

    return sku in {batch.sku for batch in batches}


def add_batch(
    ref: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: unit_of_work.AbstractUnitOfWork
):
    """Add a batch to an existing product or create a new product."""

    with uow:
        product = uow.products.get(sku)

        # Create Product aggregate if it does not exist.
        if product is None:
            product = model.Product(sku, batches=[])
            uow.products.add(product)
        else:
            product.version_number += 1

        # Create a Batch and add it to the newly created Product aggregate.
        product.batches.append(model.Batch(ref, sku, qty, eta))
        
        uow.commit()


def allocate(
    order_line: model.OrderLine,
    uow: unit_of_work.AbstractUnitOfWork
) -> str:
    """Allocate an order line through its Product aggregrate."""

    with uow:
        product = uow.products.get(order_line.sku)

        if product is None:
            raise InvalidSku(f"Invalid sku {order_line.sku}")

        batch_ref = product.allocate(order_line)  # Applies the domain rules to the product's batches.

        uow.commit()

    return batch_ref