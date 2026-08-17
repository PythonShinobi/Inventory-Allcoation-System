"""
Application service layer for the inventory allocation system.

This module contains application-level use cases that coordinate
the domain model with infrastructure such as repositories and
database sessions.

The service layer is responsible for orchestration. It retrieves
the current state of the application from a repository, performs
application-level validation, delegates business decisions to the
domain model, and persists successful changes.

It does not contain the core inventory business rules. Those rules
belong in ``app.domain.model``. It also does not handle HTTP,
JSON, or Flask-specific concerns.

Architecture::

    API / Flask
        |
        v
    Service Layer
        |
        +------> Repository
        |
        +------> Domain Model
        |
        +------> Database Session
        |
        v
    Result

Example:
    Allocate an order line against the current inventory::

        line = model.OrderLine(
            orderid="order-001",
            sku="LAMP-001",
            qty=10,
        )

        batch_ref = services.allocate(
            line=line,
            repo=repository,
            session=session,
        )

    The service layer will:

    1. Retrieve batches from the repository.
    2. Verify that the requested SKU exists.
    3. Delegate batch selection and allocation to the domain model.
    4. Commit the successful operation.
    5. Return the allocated batch reference.

The service layer depends on ``AbstractRepository`` rather than a
specific database implementation. This allows the same use case to
work with a real repository in production and a ``FakeRepository``
during unit tests.

Typical flow::

    allocate()
        |
        +-- repo.list()
        |
        +-- is_valid_sku()
        |
        +-- model.allocate()
        |
        +-- session.commit()
        |
        +-- return batch reference

Exceptions:
    InvalidSku:
        Raised when the requested SKU does not exist in the
        inventory state returned by the repository.

    model.OutOfStock:
        Raised by the domain model when no batch can satisfy
        the requested order line.

See Also:
    app.domain.model:
        Contains the domain entities, value objects, and core
        inventory allocation rules.

    app.adapters.repository:
        Defines the repository abstraction used by this service layer.
"""

from app.domain import model
from app.adapters.repository import AbstractRepository


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
        sku: The SKU to validate.
        batches: An iterable of Batch objects representing current
            inventory.

    Returns:
        True if at least one batch contains the requested SKU;
        otherwise False.
    """

    return sku in {batch.sku for batch in batches}


def allocate(
    line: model.OrderLine,
    repo: AbstractRepository,
    session,
) -> str:
    """
    Orchestrate the inventory allocation use case.

    The service retrieves the current inventory from the repository,
    validates that the requested SKU exists, delegates the actual
    allocation decision to the domain model, commits the successful
    operation, and returns the allocated batch reference.

    Args:
        line: The order line that needs to be allocated.
        repo: Repository abstraction used to retrieve inventory.
        session: Database session used to commit the operation.

    Returns:
        The reference of the batch to which the order line was allocated.

    Raises:
        InvalidSku:
            If the requested SKU does not exist in the current inventory.

        model.OutOfStock:
            If the SKU exists but no batch has sufficient available
            quantity to satisfy the order line.

    Example:
        >>> line = model.OrderLine("order-001", "LAMP-001", 10)
        >>> batch = model.Batch("batch-001", "LAMP-001", 100, eta=None)
        >>> repo = FakeRepository([batch])
        >>> session = FakeSession()
        >>> allocate(line, repo, session)
        'batch-001'

    Note:
        This function coordinates the use case but does not implement
        the core allocation rules. Batch selection and allocation
        remain the responsibility of the domain model.
    """

    # Get the current inventory state.
    batches = repo.list()

    # Validate the requested SKU against that state.
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")

    # Delegate the actual business rule to the domain.
    batch_ref = model.allocate(line, batches)

    # Persist the successful operation.
    session.commit()

    return batch_ref