# Repository

## Purpose

`app/adapters/repository.py` defines the repository abstraction and the concrete repository implementations used by the inventory allocation system.

The repository provides a consistent way for the application to **retrieve and store domain objects without knowing how those objects are persisted**.

The main architectural relationship is:

```text
                 Service Layer
                      |
                      ↓
            AbstractRepository
                  (Port)
                      ↑
             ┌────────┴────────┐
             |                 |
             ↓                 ↓
   SQLAlchemyRepository   FakeRepository
        (Adapter)             (Adapter)
             |                 |
             ↓                 ↓
         Database          Python memory
```

The service layer depends on `AbstractRepository`, not on `SqlAlchemyRepository`.

This means the service layer depends on **what it needs**, rather than on a particular persistence technology.

---

## What Is a Repository?

A repository is an abstraction that provides access to domain objects.

Instead of application code directly performing database operations:

```python
session.query(model.Batch)
session.add(batch)
```

the application can work through a repository:

```python
repo.get(reference)
repo.add(batch)
repo.list()
```

The repository hides the details of how those operations are performed.

Conceptually:

```text
Application
     |
     ↓
Repository
     |
     ↓
Persistence mechanism
```

The application therefore works with domain objects rather than directly working with database details.

---

## The Repository Port

`AbstractRepository` defines the operations that the application requires:

```python
class AbstractRepository(ABC):
    ...
```

It defines three operations:

```text
add()
get()
list()
```

These operations describe **what a repository must be able to do**.

They do not specify how the operations are implemented.

For example:

```python
repo.get("batch-001")
```

means:

> Give me the `Batch` with this reference.

The abstraction does not care whether the batch comes from:

```text
PostgreSQL
SQLite
SQLAlchemy
Python memory
another storage system
```

This makes `AbstractRepository` a **port** in the Ports and Adapters architecture.

---

## Why Use an Abstract Repository?

Without the abstraction, the service layer could become directly coupled to SQLAlchemy:

```text
Service Layer
     |
     ↓
SQLAlchemy
     |
     ↓
Database
```

The service layer would then need to understand persistence-specific code.

With the repository abstraction:

```text
Service Layer
     |
     ↓
AbstractRepository
     ↑
     |
SqlAlchemyRepository
     |
     ↓
Database
```

The service layer only knows what it needs from a repository.

This is an example of **dependency inversion**.

The application depends on an abstraction instead of depending directly on a concrete infrastructure implementation.

---

# `AbstractRepository`

```python
class AbstractRepository(ABC):
```

`AbstractRepository` defines the contract that repository implementations must follow.

It contains three abstract methods.

### `add()`

```python
def add(self, batch: model.Batch):
```

Defines that a repository must be able to store a `Batch`.

The abstraction does not say how the batch is stored.

---

### `get()`

```python
def get(self, reference: str) -> model.Batch:
```

Defines that a repository must be able to retrieve a `Batch` using its unique reference.

---

### `list()`

```python
def list(self) -> list[model.Batch]:
```

Defines that a repository must be able to return the available batches.

---

## Important Distinction

`AbstractRepository` does **not** contain the persistence implementation.

It only defines the interface required by the application.

```text
AbstractRepository

"What can the application ask a repository to do?"

        ↓

add()
get()
list()
```

The concrete adapters answer:

> "How do I actually do it?"

---

# `SqlAlchemyRepository`

```python
class SqlAlchemyRepository(AbstractRepository):
```

`SqlAlchemyRepository` is the production repository implementation.

It adapts the repository interface to SQLAlchemy.

```text
AbstractRepository
       ↑
       |
SqlAlchemyRepository
       |
       ↓
SQLAlchemy Session
       |
       ↓
Database
```

It receives a SQLAlchemy session:

```python
def __init__(self, session):
    self.session = session
```

The session provides the connection between the repository and the database.

---

## `SqlAlchemyRepository.add()`

```python
def add(self, batch: model.Batch):
    self.session.add(batch)
```

This adds the domain object to the SQLAlchemy session.

Importantly, `add()` does not commit the transaction.

The repository is responsible for persistence access, but transaction boundaries are handled elsewhere, particularly by the **Unit of Work**.

Conceptually:

```text
Repository
    |
    ↓
Add object to session
    |
    X
    |
No automatic commit
```

The Unit of Work can later decide when the transaction should be committed.

---

## `SqlAlchemyRepository.get()`

```python
def get(self, reference: str) -> model.Batch:
    return (
        self.session
        .query(model.Batch)
        .filter_by(reference=reference)
        .one()
    )
```

This retrieves a `Batch` from the database using its reference.

The important point is that the caller does not need to know that SQLAlchemy is being used.

The caller simply asks:

```python
repo.get("batch-001")
```

and receives a:

```python
model.Batch
```

---

## `SqlAlchemyRepository.list()`

```python
def list(self) -> list[model.Batch]:
    return self.session.query(model.Batch).all()
```

This retrieves all batches from the database.

Again, the SQLAlchemy query is hidden inside the repository.

---

# `FakeRepository`

```python
class FakeRepository(AbstractRepository):
```

`FakeRepository` is another implementation of the same repository port.

Instead of using a database, it stores `Batch` objects in memory:

```python
self._batches = set(batches)
```

Its architecture is:

```text
AbstractRepository
       ↑
       |
FakeRepository
       |
       ↓
Python set
```

It provides the same operations:

```text
add()
get()
list()
```

as `SqlAlchemyRepository`.

---

# Why Have a Fake Repository?

The main purpose of `FakeRepository` is testing.

A service-layer test does not necessarily need:

```text
Flask
SQLAlchemy
PostgreSQL
database tables
database connection
```

It can instead use:

```text
Service
  ↓
AbstractRepository
  ↑
FakeRepository
  ↓
Python memory
```

For example:

```python
batch = model.Batch(
    ref="batch-001",
    sku="LAMP-001",
    qty=100,
    eta=None,
)

repo = FakeRepository([batch])
```

The service can then use `repo` exactly as it would use a real repository.

This allows service-layer tests to concentrate on **business behavior** rather than database behavior.

---

# Same Interface, Different Implementation

The important property is that both repositories implement the same abstraction:

```text
                 AbstractRepository
                  /              \
                 /                \
                ↓                  ↓
     SqlAlchemyRepository    FakeRepository
                |                  |
                ↓                  ↓
            Database            Memory
```

Therefore the service layer can work with either one.

For example:

```python
def allocate(order_line, repo: AbstractRepository):
    batches = repo.list()
    ...
```

The service does not need:

```python
if production:
    use_sqlalchemy()

if testing:
    use_fake()
```

The implementation is supplied from outside.

This is **dependency injection**.

---

# Repository vs ORM

The repository and ORM have different responsibilities.

## ORM

The ORM answers:

> How does a domain object correspond to database data?

```text
Batch
  ↕
SQLAlchemy mapping
  ↕
batches table
```

This is handled by:

```text
app/adapters/orm.py
```

## Repository

The repository answers:

> How does the application retrieve and store domain objects?

```text
Service
  ↓
Repository
  ↓
ORM / SQLAlchemy
  ↓
Database
```

Therefore:

```text
ORM
→ object ↔ database mapping

Repository
→ access to persisted domain objects
```

They solve different problems.

---

# Repository vs Unit of Work

The repository and Unit of Work are also different.

### Repository

Answers:

> How do I access batches?

```python
repo.get(...)
repo.add(...)
repo.list()
```

### Unit of Work

Answers:

> What changes belong to this transaction, and when should they be committed?

Conceptually:

```text
Unit of Work
      |
      ├── Repository
      |
      ├── Repository
      |
      └── commit()
```

A use case can therefore work like:

```text
Service Layer
      |
      ↓
     UoW
      |
      ↓
 Repository
      |
      ↓
 Database
```

The repository provides access to the objects, while the Unit of Work manages the transaction boundary.

---

# What This Module Does Not Do

`repository.py` does not:

* define inventory business rules
* decide which batch should be allocated
* determine whether a batch can satisfy an order
* handle HTTP requests
* return API responses
* define database tables
* configure SQLAlchemy mappings
* decide when a transaction should commit

Those responsibilities belong elsewhere.

```text
Business rules
    → domain/model.py

Use cases
    → service_layer/services.py

Database mappings
    → adapters/orm.py

Persistence access
    → adapters/repository.py

Transaction management
    → Unit of Work

HTTP
    → entrypoints/
```

---

# Architectural Principle

The most important concept in this module is **dependency inversion**.

A naive architecture might look like:

```text
Service Layer
      ↓
SqlAlchemyRepository
      ↓
SQLAlchemy
      ↓
Database
```

The service layer is now dependent on infrastructure.

The architecture in the book instead uses:

```text
             Service Layer
                   |
                   ↓
         AbstractRepository
                   ↑
                   |
       ┌───────────┴───────────┐
       |                       |
       ↓                       ↓
SqlAlchemyRepository      FakeRepository
       |                       |
       ↓                       ↓
   Database                 Memory
```

The application defines what it needs.

Infrastructure provides implementations of those needs.

This allows infrastructure implementations to be substituted without changing the service-layer code.

---

# Main Idea

The repository pattern is therefore not primarily about databases.

It is about **separating application logic from persistence details**.

The application can say:

```python
repo.get(reference)
```

instead of needing to know:

```python
session.query(...)
```

The abstraction allows the application to work with domain objects while infrastructure handles the details of storing and retrieving them.

The central idea is:

```text
        WHAT THE APPLICATION NEEDS
                    |
                    ↓
          AbstractRepository
              (Port)
                    ↑
                    |
          HOW IT IS PROVIDED
             /          \
            /            \
           ↓              ↓
      SQLAlchemy        In Memory
       (Adapter)         (Adapter)
```

That separation is what makes the Repository pattern an important part of the book's architecture.
