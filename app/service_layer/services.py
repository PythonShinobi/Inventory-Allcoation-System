"""
Application services for the Inventory Allocation System.

This module defines the application-level operations responsible for
coordinating inventory management and order allocation.

It acts as the service layer between the API entrypoints and the
domain model. It retrieves domain objects through repositories,
invokes domain behaviour, and uses the Unit of Work to coordinate
database transactions.

Classes:
    InvalidSku:
        Application-level exception raised when an allocation request
        references a SKU that does not correspond to an existing
        product.

Functions:
    is_valid_sku(sku, batches):
        Checks whether a SKU exists among the supplied inventory
        batches.

    add_batch(ref, sku, qty, eta, uow):
        Adds a new inventory batch to an existing product or creates
        a new Product aggregate when the product does not exist.
        Commits the changes through the Unit of Work.

    allocate(order_line, uow):
        Retrieves the Product associated with an order line, validates
        that the product exists, and delegates allocation to the
        Product aggregate. Commits the successful allocation and
        returns the reference of the selected batch.

Architectural responsibilities:
    - Coordinate business operations through application services.
    - Retrieve and persist domain objects through repositories.
    - Delegate business rules to the domain model.
    - Manage transaction boundaries through the Unit of Work.
    - Raise application-level exceptions when requested products
      cannot be found.

Dependencies:
    app.domain.model:
        Provides the domain objects and business rules used by the
        application services.

    app.service_layer.unit_of_work:
        Provides the Unit of Work abstraction used to coordinate
        repository access and database transactions.

This module belongs to the application layer. It coordinates the
execution of business operations without implementing database
queries, HTTP request handling, or the core allocation rules itself.
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

    # Start unit of work context for database transactions.
    with uow:
        # uow provides SQLAlchemyProductRepository.
        product = uow.products.get(order_line.sku)

        if product is None:
            raise InvalidSku(f"Invalid sku {order_line.sku}")

        # Applies the domain rules to the product's batches.
        batch_ref = product.allocate(order_line)

        uow.commit()

    return batch_ref