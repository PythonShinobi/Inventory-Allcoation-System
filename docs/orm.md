# ORM Mapping

## Purpose

`app/adapters/orm.py` contains the SQLAlchemy ORM mappings for the inventory allocation system.

Its purpose is to connect the **domain model** to the **database** without making the domain model depend on SQLAlchemy.

The module acts as a translation layer between two different representations of the same information:

```text
Domain Model
     |
     | ORM mapping
     ↓
Database Tables
```

For example:

```text
OrderLine
      ↕
order_lines_table
```

The `OrderLine` class represents the concept in the domain, while the `order_lines` table represents the persistent form of that concept in the database.

---

## Architectural Role

`orm.py` belongs to the **infrastructure/adapters layer**.

```text
                Domain
                  |
              OrderLine
                  |
                  X
          does not know about
               SQLAlchemy
                  |
                  ↓
             adapters/orm.py
                  |
              SQLAlchemy
                  |
                  ↓
              Database
```

The dependency is intentionally directed outward from the infrastructure toward the domain.

The domain model does not import SQLAlchemy or contain database-specific declarations.

Instead, `orm.py` knows about both:

```text
orm.py
  |
  +── SQLAlchemy
  |
  +── domain.model.OrderLine
```

This allows the domain model to remain **persistence ignorant**.

---

## What ORM Means

ORM stands for **Object-Relational Mapping**.

It is the process of connecting:

```text
Object-oriented world          Relational database
---------------------------------------------------
OrderLine                  ↔   order_lines
order_id                   ↔   order_id
sku                        ↔   sku
qty                        ↔   qty
```

The domain model works with Python objects.

The database works with tables, rows, and columns.

SQLAlchemy provides the machinery that allows these two representations to work together.

---

## Database Schema

The module defines the `order_lines` table:

```text
order_lines
├── id
├── order_id
├── sku
└── qty
```

The corresponding SQLAlchemy definition is:

```python
order_lines_table = Table(
    "order_lines_table",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_id", String(255)),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
)
```

### Columns

| Column       | Type    | Purpose                        |
| ------------ | ------- | ------------------------------ |
| `id`       | Integer | Database-generated primary key |
| `order_id` | String  | Identifies the order           |
| `sku`      | String  | Identifies the product         |
| `qty`      | Integer | Quantity requested             |

The database schema is defined here rather than inside `domain/model.py` because database structure is an infrastructure concern.

---

## Metadata

```python
metadata = MetaData()
```

`MetaData` is SQLAlchemy's container for information about the database schema.

It keeps track of things such as:

* tables
* columns
* constraints
* indexes
* relationships between schema objects

In this module, `metadata` contains the definition of the `order_lines_table` table.

It can later be used to create the database schema:

```python
metadata.create_all(engine)
```

---

## Mapper Registry

```python
mapper_registry = registry()
```

The registry keeps track of SQLAlchemy's mappings between Python classes and database tables.

Conceptually:

```text
Python class                  Database table

OrderLine        ←────────→   order_lines_table
```

The registry is used to configure this relationship.

---

## Starting the Mappers

The mapping is configured by:

```python
def start_mappers():
    if mapper_registry.mappers:
        return

    mapper_registry.map_imperatively(
        OrderLine,
        order_lines_table,
    )
```

The important operation is:

```python
mapper_registry.map_imperatively(
    OrderLine,
    order_lines_table,
)
```

This tells SQLAlchemy:

> The `OrderLine` domain class is represented in the database by the `order_lines_table` table.

After the mapper has been configured, SQLAlchemy knows how to translate between the Python object and its database representation.

```text
OrderLine object
      ↕
SQLAlchemy mapper
      ↕
order_lines_table row
```

---

## Why Mapping Is Kept Outside the Domain

A simpler application could put SQLAlchemy declarations directly on the domain class.

For example, the domain class could contain SQLAlchemy-specific code.

This would create a dependency like:

```text
Domain Model
     ↓
SQLAlchemy
     ↓
Database
```

The book's architecture deliberately avoids this.

Instead:

```text
Domain Model
     ↑
     |
   Mapping
     |
     ↓
SQLAlchemy
     ↓
Database
```

The `OrderLine` class can therefore focus on representing the business concept rather than knowing how it is stored.

This is an example of **separating business concerns from infrastructure concerns**.

---

## `start_mappers()`

`start_mappers()` is responsible for configuring the mappings when the application starts.

Example:

```python
from app.adapters import orm

orm.start_mappers()
```

After this has been called, SQLAlchemy has the information necessary to persist and retrieve `OrderLine` objects.

The function also prevents the mapping from being configured repeatedly:

```python
if mapper_registry.mappers:
    return
```

If mappings already exist, the function simply returns.

---

## Relationship With the Repository

The ORM mapping and repository have different responsibilities.

### ORM

The ORM answers:

> How does this domain object correspond to database data?

```text
OrderLine
    ↕
order_lines_table
```

### Repository

The repository answers:

> How does the application retrieve and store domain objects?

Conceptually:

```text
Service Layer
      ↓
Repository
      ↓
SQLAlchemy
      ↓
Database
```

The repository can therefore use the ORM mappings without exposing database details to the service layer or domain model.

---

## What This Module Does Not Do

`orm.py` does **not**:

* implement inventory business rules
* decide whether a batch can be allocated
* allocate inventory
* handle HTTP requests
* process API input
* coordinate application use cases
* implement repository operations
* decide when a transaction should commit

Those responsibilities belong to other parts of the system.

For example:

```text
Business rules
    → domain/model.py

Use cases
    → service_layer/services.py

Persistence access
    → adapters/repository.py

Database mappings
    → adapters/orm.py

HTTP/API
    → entrypoints/
```

---

## Main Architectural Idea

The most important lesson of this module is not the SQLAlchemy syntax.

It is the separation between:

```text
Business model
      and
Persistence mechanism
```

The domain model represents **what the business means**.

The database represents **how that information is stored**.

The ORM mapping connects the two.

```text
             BUSINESS
                |
                ↓
          OrderLine object
                |
                | mapping
                ↓
            SQLAlchemy
                |
                ↓
          order_lines_table table
                |
                ↓
           DATABASE
```

This allows the persistence technology to change without requiring the business model to be rewritten around that technology.

For example, the domain model should not need to know whether the application eventually uses:

```text
PostgreSQL
SQLite
MySQL
another database
```

The infrastructure layer handles that concern.

---

## Summary

`orm.py` is the **mapping configuration between the domain model and the relational database**.

Its main responsibilities are:

1. Define database tables and columns.
2. Maintain SQLAlchemy metadata.
3. Maintain the mapper registry.
4. Map domain classes to database tables.
5. Keep persistence-specific code outside the domain model.

The central architectural relationship is:

```text
Domain Model
     |
     | independent of persistence
     ↓
ORM Mapping
     |
     | SQLAlchemy
     ↓
Database
```

The goal is to keep the **business model independent of the database and ORM**, while still allowing the application to persist domain objects.
