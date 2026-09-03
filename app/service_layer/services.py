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


def allocate(
    order_line: model.OrderLine,
    uow: unit_of_work.AbstractUnitOfWork,
) -> str:
    """
    Orchestrate the inventory allocation use case.

    The service retrieves the current inventory through the Unit of Work,
    validates that the requested SKU exists, delegates the allocation
    decision to the domain model, commits the successful operation,
    and returns the allocated batch reference.

    Args:
        order_line:
            The order line that needs to be allocated.

        uow:
            Unit of Work that provides access to repositories and
            controls the transaction.

    Returns:
        The reference of the batch to which the order line was allocated.

    Raises:
        InvalidSku:
            If the requested SKU does not exist in the current inventory.

        model.OutOfStock:
            If the SKU exists but no batch has sufficient available
            quantity to satisfy the order line.

    Note:
        This function coordinates the use case but does not implement
        the core allocation rules. Batch selection and allocation
        remain the responsibility of the domain model.
    """

    # Get the current inventory state through the Unit of Work.
    batches = uow.batches.list()

    # Validate the requested SKU against that state.
    if not is_valid_sku(order_line.sku, batches):
        raise InvalidSku(f"Invalid sku {order_line.sku}")

    # Delegate the actual business rule to the domain model.
    batch_ref = model.allocate(order_line, batches)

    # Persist the successful operation.
    uow.commit()

    return batch_ref