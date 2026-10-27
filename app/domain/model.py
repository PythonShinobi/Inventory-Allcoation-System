
"""
Domain model for the inventory allocation system.

This module defines the core business objects and rules used to
allocate customer orders to available inventory.

The domain model is responsible for deciding whether an order line
can be fulfilled, tracking inventory allocations, prioritising batches,
and raising domain exceptions when inventory is insufficient.

The module contains the following components:

    OrderLine:
        A value object representing a customer's request for a
        specific quantity of a product.

    Batch:
        An entity representing a quantity of inventory for a SKU.
        Tracks allocations, calculates available quantity, and
        determines whether an order line can be fulfilled.

    Product:
        The aggregate root that coordinates allocation across the
        batches belonging to a product. It validates the requested
        SKU, selects an eligible batch, and updates its version
        number when an allocation succeeds.

    OutOfStock:
        A domain exception raised when an order line cannot be
        allocated because the SKU does not match or sufficient
        inventory is unavailable.

Business rules:

    1. An order line can only be allocated to a batch containing
       the same SKU.
    2. A batch must have sufficient available quantity to fulfil
       the entire order line.
    3. Repeated allocation of the same order line to the same batch
       does not increase the allocated quantity.
    4. Batches already in stock are prioritised over incoming
       shipments.
    5. Among incoming shipments, batches with earlier expected
       arrival dates are prioritised.
    6. A successful allocation updates the Product aggregate's
       version number to support optimistic concurrency control.

This module contains domain logic and does not depend on the
database, web framework, or external infrastructure. Other layers
of the application coordinate persistence and expose these
business rules through application services and API endpoints.
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

        if line in self._allocations:
            raise ValueError("Order line is already allocated.")

        if not self.can_allocate(line):
            raise OutOfStock(line.sku)

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

        1. The order and batch must refer to the same product(SKU).
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

        # This batch is already in stock.
        if self.eta is None:
            # If both batches are already in stock, neither 
            # should be considered earlier than the other based on ETA.
            return other.eta is not None

        # The other batch is already in stock, so 
        # this batch should come after it.
        if other.eta is None:
            return False

        # if both batches are incoming shipments (both ETAs are dates, not None), 
        # the batch with the earlier expected arrival date comes first.
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

    def __init__(
        self, 
        sku: str, 
        batches: List[Batch],
        version_number: int = 0
    ):
        self.sku = sku
        self.batches = batches
        self.version_number = version_number

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

            self.version_number += 1

            return batch.reference

        except StopIteration:
            raise OutOfStock(f"Out of stock for sku {line.sku}")

