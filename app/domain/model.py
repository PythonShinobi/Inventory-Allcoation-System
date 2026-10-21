"""
Domain model for the inventory allocation system.

This module contains the core business concepts and rules used to
allocate customer orders against available inventory.

The domain model is intentionally independent of infrastructure.
It does not know about Flask, HTTP requests, SQLAlchemy, databases,
repositories, or API responses. It contains only the business logic
needed to represent inventory and perform allocation.

Core domain concepts:

    OrderLine
        A value object representing a product requested by a customer.

    Batch
        An entity representing a quantity of inventory belonging to
        a particular SKU.

    OutOfStock
        A domain exception raised when an order cannot be allocated.

    allocate()
        A domain service that chooses the most suitable batch for
        an order line and performs the allocation.

Allocation rules:

    1. The batch SKU must match the order-line SKU.
    2. The batch must have enough available quantity.
    3. Inventory already in stock (ETA is None) is preferred.
    4. If inventory is not currently in stock, the batch with the
       earliest ETA is preferred.
    5. If no suitable batch exists, OutOfStock is raised.

The domain model is used by the service layer. The service layer
coordinates the use case, while this module makes the actual
business decisions.

Typical flow::

    OrderLine
        |
        v
    Service Layer
        |
        v
    domain.allocate()
        |
        +--> Batch.can_allocate()
        |
        +--> Batch.allocate()
        |
        v
    Batch reference

Example::

    line = OrderLine(
        order_id="order-001",
        sku="LAMP-001",
        qty=10,
    )

    batch = Batch(
        ref="batch-001",
        sku="LAMP-001",
        qty=100,
        eta=None,
    )

    batch_ref = allocate(line, [batch])

    assert batch_ref == "batch-001"
    assert batch.available_quantity == 90

Domain responsibilities::

    - Represent inventory and customer order concepts.
    - Enforce inventory allocation rules.
    - Track allocated quantities.
    - Determine whether an allocation is possible.
    - Select the appropriate batch.
    - Report domain-level errors.

Non-responsibilities::

    - Reading or writing the database.
    - Performing SQL queries.
    - Handling HTTP requests.
    - Returning JSON responses.
    - Validating API request formats.
    - Managing application workflows.

Architectural role::

    API
      |
      v
    Service Layer
      |
      v
    Domain Model  <-- this module
      |
      v
    Business rules

The domain model should remain usable as ordinary Python code
without requiring any external infrastructure.
"""

from datetime import date
from typing import Optional, List
from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class OrderLine:
    """
    Represents a single product requested in a customer's order.

    An OrderLine is a value object. It is identified by its complete
    set of field values rather than by a separate identity.

    Because the dataclass is frozen, OrderLine instances are immutable
    and hashable. This allows them to be stored in a set and prevents
    their identifying values from changing after creation.

    Attributes:
        order_id: Unique identifier of the customer's order.
        sku: Stock Keeping Unit identifying the specific product or
            product variant being ordered.
        qty: Number of units of the SKU being requested.

    Example::

        line = OrderLine(
            order_id="order-001",
            sku="LAMP-001",
            qty=10,
        )

        line.qty
        # 10

    Two OrderLine objects with the same values are equal::

        OrderLine("order-001", "LAMP-001", 10) == \
        OrderLine("order-001", "LAMP-001", 10)

        # True
    """

    order_id: str
    sku: str
    qty: int


class Batch:
    """
    Represents a batch of inventory for a specific SKU.

    A Batch is an entity identified by its unique reference rather
    than by the values of all its attributes.

    A batch represents a quantity of inventory that can be allocated
    to customer order lines. It keeps track of which order lines have
    been allocated and calculates how much inventory remains available.

    Attributes:
        reference: Unique identifier for the batch.
        sku: SKU of the inventory contained in the batch.
        eta: Expected arrival date. ``None`` means the inventory is
            already in stock.
        _purchased_quantity: Total quantity originally purchased.
        _allocations: Order lines currently allocated to this batch.

    Example::

        batch = Batch(
            ref="batch-001",
            sku="LAMP-001",
            qty=100,
            eta=None,
        )

        batch.available_quantity
        # 100
    """

    def __init__(
        self,
        ref: str,
        sku: str,
        qty: int,
        eta: Optional[date],
    ):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations: set[OrderLine] = set()

    def allocate(self, line: OrderLine):
        """
        Allocate an order line to this batch if possible.

        The allocation succeeds only when ``can_allocate()`` returns
        True. Because allocations are stored in a set and OrderLine is
        a value object, allocating the same order line twice does not
        increase the allocated quantity.

        Args:
            line: The order line to allocate.

        Example::

            batch.allocate(line)

            batch.available_quantity
            # decreases by line.qty
        """

        if self.can_allocate(line):
            self._allocations.add(line)

    def deallocate(self, order_line: OrderLine):
        """
        Remove an order line from this batch if it is allocated.

        If the order line is not currently allocated, nothing happens.

        Args:
            order_line: The order line to remove from the allocation.
        """

        if order_line in self._allocations:
            self._allocations.remove(order_line)

    @property
    def allocated_quantity(self) -> int:
        """
        Return the total quantity currently allocated from this batch.

        The value is calculated by summing the quantities of all
        allocated order lines.
        """

        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        """
        Return the quantity of inventory that remains available.

        Available quantity is calculated as the original purchased
        quantity minus the quantity already allocated.
        """

        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, order_line: OrderLine) -> bool:
        """
        Determine whether this batch can satisfy an order line.

        A batch can allocate an order line when:

        1. The batch SKU matches the order-line SKU.
        2. The batch has enough available quantity.

        Args:
            order_line: The order line being evaluated.

        Returns:
            True if the batch can satisfy the order line,
            otherwise False.
        """

        return (
            self.sku == order_line.sku and 
            self.available_quantity >= order_line.qty
        )

    def __eq__(self, other):
        """
        Compare batches by their unique reference.

        Batch is an entity, so two batches represent the same entity
        when they have the same reference.
        """

        if not isinstance(other, Batch):
            return False

        return self.reference == other.reference

    def __hash__(self):
        """
        Return a hash based on the batch's unique reference.
        """

        return hash(self.reference)

    def __lt__(self, other):
        """
        Define the ordering used when selecting batches.

        Batches that are already in stock (``eta is None``) are
        considered earlier than incoming shipments.

        When both batches are shipments, the batch with the earlier
        ETA is considered smaller and therefore comes first when
        sorted.

        This allows::

            sorted(batches)

        to produce the allocation priority:

            1. Current stock
            2. Earliest incoming shipment
            3. Later incoming shipments
        """

        # The batch is in stock.
        if self.eta is None:
            return True

        if other.eta is None:
            return False

        return self.eta < other.eta


class OutOfStock(Exception):
    """
    Raised when an order line cannot be allocated to any batch.

    This occurs when no batch exists for the requested SKU or when
    all matching batches have insufficient available quantity.

    Attributes:
        sku: The SKU that could not be allocated.

    Example::

        raise OutOfStock("LAMP-001")
    """

    def __init__(self, sku):
        super().__init__(f"Out of stock for SKU {sku}")


class Product:
    """
    Represents a product and its associated inventory batches.

    Product is an aggregate root responsible for coordinating
    allocation across its batches. It ensures that an order line
    belongs to the product's SKU and delegates batch selection
    and allocation to the appropriate domain objects.

    Attributes:
        sku:
            The unique Stock Keeping Unit (SKU) identifying
            this product.

        batches:
            The collection of inventory batches associated
            with this product.

    Example:
        product = Product(
            sku="LAMP-001",
            batches=[batch],
        )

        batch_ref = product.allocate(order_line)
    """

    def __init__(self, sku: str, batches: List[Batch]):
        self.sku = sku
        self.batches = batches

    def allocate(self, line: OrderLine) -> str:
        """
        Allocate an order line to the most suitable batch.

        The order line must have the same SKU as the product.
        Eligible batches are considered in priority order:
        inventory already in stock first, followed by incoming
        shipments with the earliest expected arrival dates.

        Args:
            line:
                The order line to allocate to a batch.

        Returns:
            The reference of the batch that receives the allocation.

        Raises:
            OutOfStock:
                If the order line's SKU does not match this product,
                or no batch has sufficient available inventory.

        Example:
            batch_ref = product.allocate(order_line)

        This method coordinates allocation within the Product
        aggregate. Each Batch determines whether it can satisfy
        the order line and records the allocation when successful.
        """

        if line.sku != self.sku:
            raise OutOfStock(line.sku)

        try:
            batch = next(
                b
                for b in sorted(self.batches)
                if b.can_allocate(line)
            )

            batch.allocate(line)

            return batch.reference

        except StopIteration:
            raise OutOfStock(line.sku)

