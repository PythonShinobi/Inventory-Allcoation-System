"""Repositories for Product aggregates."""

from abc import ABC, abstractmethod

from app.domain import model


class AbstractProductRepository(ABC):
    """Interface for retrieving and storing Product aggregates."""
    
    @abstractmethod
    def add(self, product: model.Product) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, sku: str) -> model.Product | None:
        raise NotImplementedError


class FakeRepository(AbstractProductRepository):
    """In-memory repository for testing Product aggregates."""
    
    def __init__(self, products=()):
        self._products = {product.sku: product for product in products}

    def add(self, product: model.Product) -> None:
        self._products[product.sku] = product

    def get(self, sku: str) -> model.Product | None:
        return self._products.get(sku)