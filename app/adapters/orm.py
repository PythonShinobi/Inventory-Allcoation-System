"""
SQLAlchemy ORM mappings for the inventory allocation system.

This module defines the database schema and the mappings between
database tables and domain model classes.

Its main responsibility is to translate between two different worlds:

    Domain Model
        |
        | mapping
        v
    Database Tables

The domain model contains business concepts and rules and should not
depend on SQLAlchemy or any other persistence technology.

This module is therefore part of the infrastructure layer. It knows
about both SQLAlchemy and the domain classes and provides the mapping
that connects them.

Architecture::

    Domain Model
        |
        | OrderLine
        v
    ORM Mapping
        |
        | SQLAlchemy
        v
    Database

The domain model remains independent::

    model.OrderLine
        |
        X  does not import SQLAlchemy

while this module knows about both::

    orm.py
        |
        +--> SQLAlchemy
        |
        +--> domain.model.OrderLine

Database schema:

    order_lines
    ├── id
    ├── order_id
    ├── sku
    └── qty

The ``order_lines`` table stores the persistent representation of
the domain model's ``OrderLine`` value object.

The ``start_mappers()`` function configures SQLAlchemy so that an
``OrderLine`` object can be loaded from and persisted to the
``order_lines`` table.

Example::

    from app.domain import model
    from app.adapters import orm

    orm.start_mappers()

    line = model.OrderLine(
        order_id="order-001",
        sku="LAMP-001",
        qty=10,
    )

    # SQLAlchemy can now map the domain object to the
    # corresponding database representation.

Responsibilities::

    - Define database tables.
    - Define database columns.
    - Configure SQLAlchemy mappings.
    - Connect domain objects to their persistent representation.

Non-responsibilities::

    - Implementing inventory business rules.
    - Deciding whether a batch can be allocated.
    - Handling HTTP requests.
    - Coordinating application use cases.
    - Implementing repository operations.

Architectural role::

    Infrastructure / Data Mapping

The repository uses these mappings to persist and retrieve domain
objects while keeping database concerns outside the domain layer.
"""

from sqlalchemy.orm import registry

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
)

from app.domain.model import OrderLine


# Metadata is SQLAlchemy's container for information about your database schema.
# Think of it as a Python object that holds descriptions of your tables.
metadata = MetaData()


# Registry keeps track of which Python classes are mapped
# to which database tables
mapper_registry = registry()


# Defines the database table used to persist OrderLine objects.
#
# The important architectural point is that this table definition
# exists outside the domain model. OrderLine does not need to know
# that this table exists.
order_lines_table = Table(
    "order_lines_table",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_id", String(255)),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
)


def start_mappers():
    """
    Configure SQLAlchemy mappings between domain objects and tables.

    This function tells SQLAlchemy that ``model.OrderLine`` should be
    persisted using the ``order_lines`` table.

    The mapping is configured imperatively rather than by placing
    SQLAlchemy-specific declarations directly on the domain class.

    This keeps the domain model independent of the ORM.

    Example::

        from app.adapters import orm

        orm.start_mappers()

    After the mapper is configured, SQLAlchemy knows how to translate
    between:

        model.OrderLine
                ↕
        order_lines table

    Returns:
        None
    """

    # If this registry already contains mappings, don't configure them again.
    if mapper_registry.mappers:
        return

    # This tells SQLAlchemy model.OrderLine is represented by the order_lines table.
    mapper_registry.map_imperatively(OrderLine, order_lines_table)