from datetime import date
from typing import Optional, List
from dataclasses import dataclass

# A frozen dataclass is hashable, so Python can store it in a set
# Two OrderLine instances with the same field values are considered equal
@dataclass(frozen=True)
class OrderLine:
	"""
	Represents a single product requested in a customer's order.

	An OrderLine is a value object identified by its order ID, SKU,
	and quantity. It describes what product is being ordered and
	how many units are requested.
	"""

	orderid: str
	sku: str
	qty: int


class Batch:
	"""
	Represents a batch of purchased inventory for a specific product.

	A Batch is an entity identified by its unique reference. It tracks
	the purchased quantity of a single SKU, manages allocations to
	customer order lines, and determines how much stock is still
	available.
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
		self._allocations: set[OrderLine] = set()  # A set of OrderLine objects

	def allocate(self, line: OrderLine):
		if self.can_allocate(line):
			self._allocations.add(line)

	def deallocate(self, line: OrderLine):
		if line in self._allocations:
			self._allocations.remove(line)

	@property
	def allocated_quantity(self) -> int:
		return sum(
			line.qty
			for line in self._allocations
		)

	@property
	def available_quantity(self) -> int:
		return self._purchased_quantity - self.allocated_quantity

	def can_allocate(self, line: OrderLine) -> bool:
		return (
			self.sku == line.sku
			and self.available_quantity >= line.qty
		)

	def __eq__(self, other):
		if not isinstance(other, Batch):
			return False

		return self.reference == other.reference

	def __hash__(self):
		return hash(self.reference)

	def __lt__(self, other):
		if self.eta is None:
			return True
		
		if other.eta is None:
			return False
		
		return self.eta < other.eta


class OutOfStock(Exception):
    """
    Exception raised when no available batch can fulfill an order line.

    This occurs when all matching batches have insufficient available
    quantity or when no batch exists for the requested SKU.
    """
    
    def __init__(self, sku):
        super().__init__(f"Out of stock for SKU {sku}")


def allocate(line: OrderLine, batches: List[Batch]) -> str:
    """
    Allocates an order line to the most suitable batch.

    The batches are sorted so that warehouse stock (ETA is None) is
    preferred over incoming shipments, and shipment batches are
    considered in order of their earliest arrival date. The first
    batch that can satisfy the order line is allocated, and its
    reference is returned.

    Args:
        line: The customer order line to allocate.
        batches: The available batches to allocate from.

    Returns:
        The reference of the batch that the order line was allocated to.

    Raises:
        OutOfStock: If no batch can allocate the order line.
    """
	
    try:
		# next() simply returns the first matching item from the generator expression
        batch = next(
            b for b in sorted(batches) if b.can_allocate(line)
        )
				
    except StopIteration:
        raise OutOfStock(line.sku)

    batch.allocate(line)
		
    return batch.reference