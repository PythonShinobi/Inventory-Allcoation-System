
# Unit of Work

## Purpose

The Unit of Work is responsible for managing the **transaction boundary** of an application operation.

It provides:

* Access to the repositories required by the operation.
* A database transaction that groups changes together.
* A way to commit successful changes.
* A way to roll back uncommitted changes.
* Management of the database session lifecycle.

The Unit of Work allows the service layer to work with transactions without depending directly on SQLAlchemy.

---

# What Is the Unit of Work?

A Unit of Work represents a collection of operations that should be treated as **one transaction**.

For example, an application operation might:

1. Retrieve some objects.
2. Modify those objects.
3. Create new objects.
4. Commit all changes together.

The Unit of Work provides the boundary around those operations.

Conceptually:

```text
Application Operation
        |
        v
   Unit of Work
        |
        +---- Repository
        |
        +---- Database Session
        |
        v
     Commit / Rollback
```

The important idea is that the service layer does not need to manage the database transaction itself.

---

# Why Use a Unit of Work?

Without a Unit of Work, application services could become responsible for managing database sessions and transactions directly.

That would couple the service layer to the persistence technology.

For example, a service would need to know about:

```text
SQLAlchemy Session
    |
    +-- commit()
    +-- rollback()
    +-- close()
```

Instead, the service layer works with:

```text
AbstractUnitOfWork
    |
    +-- batches
    +-- commit()
    +-- rollback()
```

The service therefore depends on an abstraction rather than directly depending on SQLAlchemy.

---

# AbstractUnitOfWork

The `AbstractUnitOfWork` defines the interface that every Unit of Work must provide.

```python
class AbstractUnitOfWork(ABC):
    batches: repository.AbstractRepository
```

The `batches` attribute is a type annotation.

It does **not** create a repository or determine which repository implementation will be used.

It only states that a Unit of Work must provide a `batches` repository that follows the `AbstractRepository` interface.

Concrete implementations are responsible for providing the actual repository.

---

# The `batches` Repository

The Unit of Work exposes the repository through:

```python
batches: repository.AbstractRepository
```

This creates an architectural boundary between the service layer and the concrete repository implementation.

The service layer can write:

```python
uow.batches.list()
```

without knowing whether `batches` is backed by:

* SQLAlchemy
* an in-memory collection
* another database technology
* a fake repository used in tests

The concrete Unit of Work determines what object is actually assigned to `batches`.

---

# Entering the Unit of Work

The abstract implementation defines:

```python
def __enter__(self):
    return self
```

This allows the Unit of Work to be used with Python's `with` statement:

```python
with uow:
    ...
```

When execution enters the `with` block, the Unit of Work returns itself.

This allows the code inside the block to access:

```python
uow.batches
uow.commit()
```

and other Unit of Work operations.

---

# Leaving the Unit of Work

The abstract implementation defines:

```python
def __exit__(self, *args):
    self.rollback()
```

When execution leaves the `with` block, `rollback()` is called.

This provides a safety mechanism for changes that were not explicitly committed.

The design therefore follows the principle:

```text
Start transaction
      |
      v
Perform operations
      |
      +---- commit() ----> Keep changes
      |
      +---- no commit ---> Roll back
      |
      v
End transaction
```

The service explicitly calls `commit()` when the operation succeeds.

If execution leaves the context without reaching the commit, the Unit of Work rolls back.

---

# Commit

The abstract Unit of Work declares:

```python
@abstractmethod
def commit(self):
    raise NotImplementedError
```

The abstract class does not know how data is actually persisted.

It only defines the requirement:

> A concrete Unit of Work must provide a way to commit the current transaction.

The concrete implementation decides how that happens.

---

# Rollback

The abstract Unit of Work also declares:

```python
@abstractmethod
def rollback(self):
    raise NotImplementedError
```

This defines the requirement that a concrete Unit of Work must be able to discard uncommitted changes.

Again, the abstract class does not depend on a specific database technology.

---

# SQLAlchemyUnitOfWork

`SQLAlchemyUnitOfWork` is the concrete implementation of `AbstractUnitOfWork`.

```python
class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
```

Its responsibility is to connect the abstract Unit of Work interface to SQLAlchemy.

It provides:

* a SQLAlchemy session
* a SQLAlchemy repository
* commit behavior
* rollback behavior
* session cleanup

The architecture is therefore:

```text
AbstractUnitOfWork
        ^
        |
SQLAlchemyUnitOfWork
        |
        +---- SQLAlchemy Session
        |
        +---- SqlAlchemyRepository
```

---

# Session Factory

The SQLAlchemy Unit of Work receives a `session_factory`:

```python
def __init__(self, session_factory):
    self.session_factory = session_factory
```

The Unit of Work does not create the SQLAlchemy session itself.

Instead, it receives a callable capable of creating one.

This allows session creation to be controlled from outside the Unit of Work.

When the Unit of Work starts, it calls:

```python
self.session = self.session_factory()
```

A new database session is therefore created for that Unit of Work.

---

# Creating the Repository

Inside `__enter__()`:

```python
self.batches = repository.SqlAlchemyRepository(self.session)
```

This is where the concrete repository implementation is selected.

The abstract class said:

```python
batches: repository.AbstractRepository
```

but it did not choose an implementation.

The concrete SQLAlchemy Unit of Work now provides:

```python
SqlAlchemyRepository
```

Therefore:

```python
uow.batches
```

actually refers to a `SqlAlchemyRepository` when using `SQLAlchemyUnitOfWork`.

So:

```python
uow.batches.list()
```

ultimately calls the `list()` implementation provided by `SqlAlchemyRepository`.

---

# Repository vs Unit of Work

The Repository and Unit of Work have different responsibilities.

## Repository

The Repository is responsible for **accessing domain objects**.

Its question is:

> How do I retrieve, add, or store these objects?

For example:

```python
uow.batches.list()
uow.batches.add(batch)
uow.batches.get(reference)
```

## Unit of Work

The Unit of Work is responsible for the **transaction**.

Its question is:

> What operations belong to the same transaction, and when are those changes committed or rolled back?

For example:

```python
uow.commit()
uow.rollback()
```

So:

```text
Repository
    = object persistence/access

Unit of Work
    = transaction management
```

---

# Unit of Work and the Service Layer

The service layer depends on the abstract Unit of Work:

```python
def allocate(
    order_line: model.OrderLine,
    uow: unit_of_work.AbstractUnitOfWork,
):
```

The service does not need to know that SQLAlchemy is being used.

It can simply perform:

```python
batches = uow.batches.list()

...

uow.commit()
```

The concrete implementation is supplied from outside the service layer.

This keeps the service layer independent from the persistence technology.

---

# Transaction Boundary

The Unit of Work defines where a transaction begins and ends.

Conceptually:

```text
with uow:
    |
    |-- retrieve data
    |
    |-- modify data
    |
    |-- perform business operation
    |
    |-- commit()
    |
    v
transaction ends
```

Everything performed within the Unit of Work participates in the same transaction.

This is particularly important when an application operation makes multiple changes that must succeed or fail together.

---

# Explicit Commit

The application service explicitly calls:

```python
uow.commit()
```

when the operation succeeds.

This makes the commit decision visible in the service layer.

The general flow is:

```text
Start UoW
    |
    v
Perform operation
    |
    v
Successful?
   / \
 yes  no
  |    |
  v    v
commit rollback
```

If an exception occurs before the commit, leaving the Unit of Work causes `rollback()` to be called.

---

# Session Lifecycle

The SQLAlchemy Unit of Work manages the lifetime of the database session.

When entering:

```python
self.session = self.session_factory()
```

A new session is created.

When leaving:

```python
self.session.close()
```

the session is closed.

The lifecycle is therefore:

```text
__enter__()
    |
    +-- create session
    |
    +-- create repository
    |
    v
perform application operation
    |
    v
__exit__()
    |
    +-- rollback
    |
    +-- close session
```

The session therefore belongs to the lifetime of the Unit of Work.

---

# Why the Repository Is Created Inside the Unit of Work

The repository is created using the Unit of Work's session:

```python
self.batches = repository.SqlAlchemyRepository(self.session)
```

This means the repository operates using the same database session managed by the Unit of Work.

The relationship is:

```text
SQLAlchemyUnitOfWork
        |
        +---- session
        |
        +---- batches repository
                  |
                  +---- uses same session
```

The Unit of Work therefore coordinates the repository and the transaction.

---

# Abstract vs Concrete Unit of Work

There are two different roles.

## AbstractUnitOfWork

Defines the contract:

```python
class AbstractUnitOfWork(ABC):
```

It says that a Unit of Work must provide:

```text
batches
commit()
rollback()
```

It does not know how those operations are implemented.

## SQLAlchemyUnitOfWork

Provides the actual implementation:

```python
class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
```

It connects the contract to SQLAlchemy:

```text
AbstractUnitOfWork
        |
        v
SQLAlchemyUnitOfWork
        |
        +-- SQLAlchemy session
        +-- SqlAlchemyRepository
        +-- session.commit()
        +-- session.rollback()
```

---

# Testing

The abstract Unit of Work also makes the service layer easier to test.

Tests do not need to use the real SQLAlchemy Unit of Work.

A test can provide another implementation:

```text
Service Layer
      |
      v
AbstractUnitOfWork
      |
      +---- Production
      |       |
      |       +-- SQLAlchemyUnitOfWork
      |
      +---- Tests
              |
              +-- FakeUnitOfWork
```

The service layer remains unchanged.

Only the concrete Unit of Work supplied to it changes.

This allows service-layer tests to focus on application behavior without requiring a real database.

---

# Unit of Work vs Service Layer

The two components solve different problems.

### Service Layer

Defines the steps of an application use case.

```text
What does the application operation need to do?
```

### Unit of Work

Defines the transaction boundary for that operation.

```text
Which changes belong to the same transaction?
```

The service orchestrates the operation.

The Unit of Work manages the transaction in which that operation takes place.

---

# Unit of Work vs Repository

A useful distinction is:

```text
Repository
    "Give me the objects I need."

Unit of Work
    "Manage the transaction containing my operations."
```

The Repository provides access to persistent objects.

The Unit of Work coordinates those repositories within a transaction.

---

# Position in the Architecture

The Unit of Work sits between the service layer and persistence infrastructure.

```text
        API / Flask
             |
             v
       Service Layer
             |
             v
    AbstractUnitOfWork
             |
             v
   SQLAlchemyUnitOfWork
             |
       +-----+-----+
       |           |
       v           v
 Repository     Session
       |           |
       +-----+-----+
             |
             v
          Database
```

The service layer depends on the abstraction.

The infrastructure layer provides the concrete implementation.

---

# Main Architectural Idea

The Unit of Work separates **application operations** from **transaction management**.

The service layer should be concerned with:

```text
What should happen?
```

The repository should be concerned with:

```text
How do I access persistent objects?
```

The Unit of Work should be concerned with:

```text
How are these operations grouped into a transaction?
```

The database implementation should be concerned with:

```text
How are those operations actually persisted?
```

This separation keeps each component focused on a specific responsibility and prevents database-specific transaction management from spreading throughout the application.
