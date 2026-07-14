from datetime import date
from typing import Optional
from dataclasses import dataclass

# A frozen dataclass is hashable, so Python can store it in a set
# Two OrderLine instances with the same field values are considered equal
@dataclass(frozen=True)
class OrderLine:
	orderid: str
	sku: str
	qty: int


class Batch:
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
			self.sku == line.sku and
			self._purchased_quantity >= line.qty
		)