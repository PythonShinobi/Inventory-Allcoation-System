# ORM Mapping

## Purpose

`app/adapters/orm.py` contains the SQLAlchemy ORM mappings for the inventory allocation system.

Its responsibility is to connect the **domain model** to the **relational database** without making the domain model depend on SQLAlchemy.

The module connects two different worlds:

```text
Domain Model
     |
     | ORM Mapping
     ↓
Database Tables
```

The domain model works with Python objects such as:

```text
OrderLine
Batch
```

while the database works with:

```text
Tables
Rows
Columns
Foreign Keys
```

The ORM mapping tells SQLAlchemy how these two representations correspond to each other.

---

# Architectural Role

`orm.py` belongs to the **infrastructure / adapters layer**.

```text
                Domain Model
                     |
             OrderLine / Batch
                     |
                     X
          Does not know about
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

The domain model remains independent of persistence technology.

`orm.py`, on the other hand, knows about both:

```text
orm.py
  |
  +── SQLAlchemy
  |
  +── domain.model.OrderLine
  |
  +── domain.model.Batch
```

This allows the domain model to focus on business concepts and rules while the infrastructure layer handles persistence.

---

# What ORM Means

ORM stands for **Object-Relational Mapping**.

It is the process of mapping objects in an object-oriented program to data stored in relational database tables.

Conceptually:

```text
Python Object                 Database
---------------------------------------------
OrderLine              ↔      order_lines_table
Batch                  ↔      batches_table
Batch._allocations     ↔      allocations
```

The ORM is responsible for understanding how these representations correspond.

---

# Database Tables

This module defines three database tables:

```text
order_lines_table
batches_table
allocations
```

They represent different parts of the domain model.

The overall relationship is:

```text
OrderLine
    |
    | stored in
    ↓
order_lines_table


Batch
    |
    | stored in
    ↓
batches_table


Batch
    |
    | has allocations
    ↓
allocations
    |
    | connects to
    ↓
OrderLine
```

---

# Metadata

The module creates a SQLAlchemy `MetaData` object:

```python
metadata = MetaData()
```

`MetaData` is SQLAlchemy's container for information describing the database schema.

It keeps track of the tables and other schema objects defined by the application.

In this module, the following tables are registered with `metadata`:

```text
order_lines_table
batches_table
allocations
```

The metadata can later be associated with a database engine to create the defined schema.

---

# Mapper Registry

The module creates a SQLAlchemy mapper registry:

```python
mapper_registry = registry()
```

The registry keeps track of the mappings between Python classes and database tables.

Conceptually:

```text
Python Class              Database Table

OrderLine       ↔         order_lines_table

Batch           ↔         batches_table
```

The mappings are configured inside `start_mappers()`.

---

# `order_lines_table`

The first table represents `OrderLine` objects:

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

Its structure is:

```text
order_lines_table
├── id
├── order_id
├── sku
└── qty
```

| Column       | Type    | Purpose                |
| ------------ | ------- | ---------------------- |
| `id`       | Integer | Database primary key   |
| `order_id` | String  | Identifies the order   |
| `sku`      | String  | Identifies the product |
| `qty`      | Integer | Requested quantity     |

The `id` column is a database-level identifier for the row.

The domain object does not need to know about this database-specific identifier.

---

# `batches_table`

The second table represents `Batch` objects:

```python
batches_table = Table(
    "batches_table",
    metadata,
    Column("reference", String(255), primary_key=True),
    Column("sku", String(255)),
    Column("_purchased_quantity", Integer),
    Column("eta", Date, nullable=True)
)
```

Its structure is:

```text
batches_table
├── reference
├── sku
├── _purchased_quantity
└── eta
```

| Column                  | Type    | Purpose                        |
| ----------------------- | ------- | ------------------------------ |
| `reference`           | String  | Identifies the batch           |
| `sku`                 | String  | Product contained in the batch |
| `_purchased_quantity` | Integer | Quantity originally purchased  |
| `eta`                 | Date    | Expected arrival date          |

The `reference` column is the primary key.

This corresponds to the identity of a `Batch` entity in the domain model.

---

# Mapping `OrderLine`

The `OrderLine` class is mapped using:

```python
mapper_registry.map_imperatively(
    OrderLine,
    order_lines_table,
)
```

This tells SQLAlchemy:

> Map the `OrderLine` Python class to the `order_lines_table` database table.

The relationship can therefore be thought of as:

```text
OrderLine object
      ↕
SQLAlchemy Mapper
      ↕
order_lines_table row
```

The mapping is **imperative** because the mapping configuration is written separately from the domain class.

The domain class itself does not contain SQLAlchemy mapping declarations.

---

# Mapping `Batch`

`Batch` is also mapped:

```python
mapper_registry.map_imperatively(
    Batch,
    batches_table,
    properties={
        "_allocations": relationship(
            OrderLine,
            secondary=allocations_table,
            collection_class=set,
        )
    },
)
```

This does two things:

1. Maps the basic `Batch` attributes to `batches_table`.
2. Maps the `_allocations` relationship to `OrderLine`.

The basic mapping is:

```text
Batch
  ↕
batches_table
```

But `Batch` also contains:

```python
_allocations
```

which represents the `OrderLine` objects allocated to that batch.

That requires an additional database relationship.

---

# The `allocations_table`

The `allocations` table connects batches and order lines:

```python
allocations_table = Table(
    "allocations",
    metadata,
    Column(
        "orderline_id",
        Integer,
        ForeignKey("order_lines_table.id"),
    ),
    Column(
        "batch_id",
        String(255),
        ForeignKey("batches_table.reference"),
    ),
)
```

Its structure is:

```text
allocations
├── orderline_id
└── batch_id
```

The table contains two foreign keys:

```text
orderline_id
      |
      ↓
order_lines_table.id


batch_id
      |
      ↓
batches_table.reference
```

Conceptually:

```text
batches_table
      |
      | batch_id
      ↓
allocations
      ↑
      | orderline_id
      |
order_lines_table
```

This table allows the database to represent which `OrderLine` objects are allocated to which `Batch`.

---

# Why `allocations` Is a Separate Table

The domain model contains:

```python
_allocations: set[OrderLine]
```

A batch can therefore have multiple order lines allocated to it.

A relational database cannot simply store a Python `set` of `OrderLine` objects inside one column.

Instead, the relationship is represented using a separate table:

```text
Batch
  |
  | one or more allocations
  ↓
allocations
  |
  | references
  ↓
OrderLine
```

The `allocations` table therefore acts as a **link table** between `Batch` and `OrderLine`.

---

# SQLAlchemy Relationship

The relationship is configured with:

```python
relationship(
    OrderLine,
    secondary=allocations_table,
    collection_class=set,
)
```

### `OrderLine`

This tells SQLAlchemy that the relationship contains `OrderLine` objects.

```text
Batch
  |
  ↓
OrderLine
```

### `secondary=allocations_table`

This tells SQLAlchemy that the relationship is maintained through the `allocations` table.

```text
Batch
  |
  ↓
allocations
  |
  ↓
OrderLine
```

### `collection_class=set`

The domain model represents allocations as a Python `set`.

The mapping preserves that collection behavior:

```text
Domain:

_allocations = set[OrderLine]

        ↕

SQLAlchemy relationship

        ↕

allocations table
```

This allows the persistence representation to support the collection abstraction expected by the domain model.

---

# Why `_allocations` Is Not a Column

The `Batch` class contains:

```python
_allocations
```

but there is no corresponding column such as:

```python
Column("_allocations", ...)
```

This is intentional.

`_allocations` is not a piece of scalar data such as:

```text
reference
sku
quantity
eta
```

Instead, it represents a **relationship between objects**.

Therefore SQLAlchemy maps it using:

```python
relationship(...)
```

rather than:

```python
Column(...)
```

The distinction is:

```text
Simple attribute
      ↓
Column

Object relationship
      ↓
relationship()
```

---

# `start_mappers()`

The `start_mappers()` function configures all ORM mappings:

```python
def start_mappers():
    if mapper_registry.mappers:
        return

    mapper_registry.map_imperatively(
        OrderLine,
        order_lines_table,
    )

    mapper_registry.map_imperatively(
        Batch,
        batches_table,
        properties={
            "_allocations": relationship(
                OrderLine,
                secondary=allocations_table,
                collection_class=set,
            )
        },
    )
```

It performs two mappings:

```text
OrderLine
    ↕
order_lines_table
```

and:

```text
Batch
    ↕
batches_table

Batch._allocations
    ↕
allocations
    ↕
OrderLine
```

---

# Preventing Duplicate Mappings

The function begins with:

```python
if mapper_registry.mappers:
    return
```

This prevents the mappings from being configured more than once.

Once SQLAlchemy already has mappings registered, calling `start_mappers()` again simply returns.

This is useful because application startup or tests may cause the mapper initialization function to be called multiple times.

---

# Imperative Mapping

The application uses imperative mapping:

```python
mapper_registry.map_imperatively(...)
```

rather than placing SQLAlchemy-specific declarations directly inside the domain classes.

This means the domain model can remain ordinary Python code.

Conceptually:

```text
domain/model.py

OrderLine
Batch

        ↑
        |
        | mapped externally
        |
orm.py

        |
        ↓
   SQLAlchemy
        |
        ↓
    Database
```

The mapping is therefore an infrastructure concern rather than a domain concern.

---

# Persistence Ignorance

One of the important architectural goals of this design is that the domain model does not need to know how persistence works.

The domain model should be able to operate as:

```python
OrderLine(...)
Batch(...)
```

without requiring:

```python
from sqlalchemy import ...
```

or:

```python
Column(...)
relationship(...)
```

The database concerns are kept in `orm.py`.

This creates a boundary between:

```text
Business Logic
```

and:

```text
Persistence Technology
```

---

# Relationship With the Repository

The ORM and Repository have different responsibilities.

## ORM

The ORM defines:

> How are domain objects represented in the database?

For example:

```text
Batch
  ↕
batches_table
```

and:

```text
Batch._allocations
  ↕
allocations
  ↕
OrderLine
```

## Repository

The Repository defines:

> How does the application retrieve and persist those domain objects?

Conceptually:

```text
Service Layer
      ↓
Unit of Work
      ↓
Repository
      ↓
SQLAlchemy ORM
      ↓
Database
```

The repository uses the persistence infrastructure but hides those details from the service layer.

---

# Relationship With the Unit of Work

The Unit of Work manages the SQLAlchemy session and provides the repository.

The ORM defines how the domain objects are mapped.

The relationship is:

```text
Service Layer
      |
      ↓
Unit of Work
      |
      ↓
Repository
      |
      ↓
SQLAlchemy Session
      |
      ↓
ORM Mappings
      |
      ↓
Database
```

The Unit of Work is responsible for the transaction.

The Repository is responsible for persistence access.

The ORM is responsible for object-relational mapping.

---

# What This Module Does Not Do

`orm.py` does not:

* implement inventory business rules
* decide whether a batch can be allocated
* perform allocation
* validate orders
* coordinate application use cases
* handle HTTP requests
* define API responses
* manage application transactions
* implement repository methods

Those responsibilities belong elsewhere.

```text
Business rules
    → domain/model.py

Application use cases
    → service_layer/services.py

Transaction management
    → service_layer/unit_of_work.py

Persistence access
    → adapters/repository.py

Object-relational mapping
    → adapters/orm.py

HTTP/API
    → entrypoints/
```

---

# Main Architectural Idea

The important concept in `orm.py` is **separation between the domain model and persistence**.

The domain model represents the business concepts:

```text
OrderLine
Batch
```

The database represents persistent data:

```text
order_lines_table
batches_table
allocations
```

The ORM mapping connects the two:

```text
             DOMAIN
                |
                ↓
          OrderLine / Batch
                |
                | ORM mapping
                ↓
            SQLAlchemy
                |
                ↓
        Database Tables
                |
       +--------+--------+
       |        |        |
       ↓        ↓        ↓
  order_lines batches allocations
```

The domain model does not need to know that these tables exist.

The infrastructure layer provides the translation.

---

# Summary

`app/adapters/orm.py` is responsible for configuring how the domain model is represented in the relational database.

Its responsibilities are:

1. Define the database tables.
2. Define columns and constraints.
3. Create SQLAlchemy metadata.
4. Maintain the mapper registry.
5. Map `OrderLine` to `order_lines_table`.
6. Map `Batch` to `batches_table`.
7. Map `Batch._allocations` to `OrderLine` through `allocations`.
8. Preserve the domain model's allocation collection as a `set`.
9. Keep SQLAlchemy-specific persistence concerns outside the domain model.

The resulting architecture is:

```text
                    DOMAIN
                      |
             +--------+--------+
             |                 |
         OrderLine           Batch
             |                 |
             |                 |
             +--------+--------+
                      |
                      | ORM Mapping
                      ↓
                  SQLAlchemy
                      |
              +-------+-------+
              |       |       |
              ↓       ↓       ↓
        order_lines batches allocations
              |       |       |
              +-------+-------+
                      |
                      ↓
                   DATABASE
```

The central idea is:

> **The domain model describes the business; the ORM describes how that business data is persisted.**

Keeping those responsibilities separate prevents database technology from becoming part of the core domain model.
