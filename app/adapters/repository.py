"""
Repository abstractions for the Inventory Allocation System.

This module defines the repository interface and its concrete
implementations for retrieving and storing Product aggregates.

The Repository pattern separates domain objects from the details
of data access. Application services interact with repositories
through a common interface without needing to know how products
are retrieved or persisted.

Classes:
    AbstractProductRepository:
        Defines the contract for product repositories. Declares
        the operations required to add and retrieve Product
        aggregates.

    SQLAlchemyProductRepository:
        Implements product persistence using SQLAlchemy. Uses a
        database session to add products and retrieve existing
        products by their SKU.

    FakeRepository:
        Provides an in-memory implementation of the repository
        interface. Stores Product objects in a dictionary indexed
        by SKU and is primarily used for service-layer testing.

Responsibilities:
    - Define a consistent interface for product data access.
    - Retrieve Product aggregates using their SKU.
    - Add new Product aggregates to the persistence session.
    - Separate application logic from database implementation.
    - Support alternative repository implementations for testing.

Repository operations:
    add(product):
        Adds a Product aggregate to the repository.

    get(sku):
        Retrieves the Product aggregate associated with the
        specified SKU, or returns None if no matching product
        exists.

Architectural responsibility:
    This module belongs to the adapter and infrastructure layer.

    AbstractProductRepository provides the abstraction used by
    application services and the Unit of Work.

    SQLAlchemyProductRepository provides the database-backed
    implementation, while FakeRepository provides an in-memory
    implementation for testing.

    Both implementations follow the same repository interface,
    allowing application services to work independently of the
    underlying persistence mechanism.

The repository handles data access and persistence coordination.
It does not implement inventory allocation rules, which belong
to the domain model.
"""

from sqlalchemy.orm import Session
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


class SQLAlchemyProductRepository(AbstractProductRepository):
    """SQLAlchemy repository for Product aggregates. Loads and saves
    product models and commits changes to the database."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, product: model.Product) -> None:
        self.session.add(product)

    def get(self, sku: str) -> model.Product | None:
        # Return the first record that matches the SKU.
        return (
            self.session.query(model.Product)
            .filter_by(sku=sku)
            .first()
        )


class FakeRepository(AbstractProductRepository):
    """In-memory repository for testing Product aggregates."""
    
    def __init__(self, products=()):
        self._products = {product.sku: product for product in products}

    def add(self, product: model.Product) -> None:
        self._products[product.sku] = product

    def get(self, sku: str) -> model.Product | None:
        return self._products.get(sku)