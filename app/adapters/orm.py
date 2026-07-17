from sqlalchemy.orm import registry
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String
)

from app.domain import model


# Container that stores information about all the database 
# tables in your application.
metadata = MetaData()

# Responsible for connecting your Python objects to
# database tables
mapper_registry = registry()

# Defines the database schema for storing customer order lines.
# This table is mapped to the domain model's OrderLine class
# without introducing SQLAlchemy dependencies into the domain layer.
order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("orderid", String(255)),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
)


def start_mappers():
    """
    Configure SQLAlchemy mappings between the domain model and
    the database tables.

    This function registers the mapping that allows SQLAlchemy to
    load and persist domain objects without introducing database
    dependencies into the domain model.
    """
    mapper_registry.map_imperatively(
        model.OrderLine,
        order_lines,
    )