
"""
SQLAlchemy ORM mappings for the inventory allocation system.

This module defines database tables and maps them to domain classes.
The domain model remains independent of SQLAlchemy.
"""

from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
)
from sqlalchemy.orm import registry, relationship

from app.domain.model import OrderLine, Batch, Product


# Stores the definitions of all database tables.
metadata = MetaData()

# Registers the mappings between Python classes and database tables.
mapper_registry = registry()


# OrderLine value objects are stored in this table.
order_lines_table = Table(
    "order_lines_table",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_id", String(255), nullable=False),
    Column("sku", String(255), nullable=False),
    Column("qty", Integer, nullable=False),
)


# Product is the aggregate root for batches belonging to a SKU.
products_table = Table(
    "products",
    metadata,
    Column("sku", String(255), primary_key=True),
    Column("version_number", Integer, nullable=False, default=0),
)


# Each batch belongs to a Product.
batches_table = Table(
    "batches_table",
    metadata,
    Column("reference", String(255), primary_key=True),
    Column("sku", String(255), ForeignKey("products.sku"), nullable=False),
    Column("_purchased_quantity", Integer, nullable=False),
    Column("eta", Date, nullable=True),
)


# Connects allocated order lines to their batches.
allocations_table = Table(
    "allocations",
    metadata,
    Column("orderline_id", Integer, ForeignKey("order_lines_table.id"), primary_key=True),
    Column("batch_id", String(255), ForeignKey("batches_table.reference"), primary_key=True),
)


def start_mappers():
    """
    Configure the SQLAlchemy mappings once.

    Product is the aggregate root. Its batches are loaded through
    the Product.batches relationship.

    Product.version_number is used for optimistic concurrency control.
    The domain model is responsible for incrementing the version when
    the aggregate changes.
    """
    if mapper_registry.mappers:
        return

    mapper_registry.map_imperatively(
        OrderLine,
        order_lines_table,
    )

    mapper_registry.map_imperatively(
        Product,
        products_table,
        properties={
            "batches": relationship(Batch),
        },
        version_id_col=products_table.c.version_number,
        version_id_generator=False,
    )

    mapper_registry.map_imperatively(
        Batch,
        batches_table,
        properties={
            "_allocations": relationship(
                OrderLine,
                secondary=allocations_table,
                collection_class=set,
            ),
        },
    )
