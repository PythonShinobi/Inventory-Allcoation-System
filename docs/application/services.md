# Service Layer

## Purpose

`app/service_layer/services.py` contains the **application service layer** for the inventory allocation system.

Its responsibility is to coordinate application use cases.

The service layer sits between the outside world, such as the API, and the domain model:

```text
API / Flask
     |
     ↓
Service Layer
     |
     ↓
Unit of Work
     |
     ├── Repository
     |
     └── Transaction
```

The service layer answers:

> **What steps need to happen to complete this application use case?**

It does not contain the core business rules themselves.

---

# What Is the Service Layer?

The service layer is an **orchestration layer**.

It coordinates different parts of the system to perform a complete use case.

For the inventory system, one use case is:

```text
Allocate an order line
```

The service layer coordinates the steps required to perform that operation:

```text
allocate()
    |
    ├── Get inventory through Unit of Work
    |
    ├── Validate SKU
    |
    ├── Ask domain model to allocate
    |
    ├── Commit successful change
    |
    └── Return batch reference
```

The service layer therefore connects the pieces of the architecture without taking ownership of the business rules.

---

# Architectural Position

The service layer sits between the application's entrypoints and the domain:

```text
                 HTTP Request
                      |
                      ↓
                Flask / API
                      |
                      ↓
              Service Layer
                      |
                      ↓
              Abstract Unit of Work
                      |
          ┌───────────┴───────────┐
          ↓                       ↓
     Repository              Transaction
          |                       |
          ↓                       ↓
      Database                Commit/
                              Rollback

                      |
                      ↓
                 Domain Model
                      |
                      ↓
                Business Rules
```

The API should not need to know how inventory allocation works.

The domain should not need to know how HTTP requests or database sessions work.

The service layer coordinates these components through the Unit of Work.

---

# The Service Layer Does Not Own the Business Rules

This distinction is important.

The service layer contains **application logic**, while the domain model contains **business logic**.

For example, the domain model knows rules such as:

```text
A batch can only be allocated when:

- The SKU matches.
- Enough quantity is available.
- The order line has not already been allocated.
```

The domain model also decides which batch should be preferred.

The service layer does not reproduce those rules.

Instead, it calls:

```python
model.allocate(order_line, batches)
```

The domain model makes the allocation decision.

Conceptually:

```text
Service Layer
     |
     | "Allocate this order."
     ↓
Domain Model
     |
     | "According to the business rules,
     |  this batch should be used."
     ↓
Batch
```

This prevents business rules from becoming scattered across the application.

---

# `InvalidSku`

```python
class InvalidSku(Exception):
```

`InvalidSku` represents an application-level validation failure.

It is raised when the requested SKU does not exist in the current inventory state.

```python
if not is_valid_sku(order_line.sku, batches):
    raise InvalidSku(f"Invalid sku {order_line.sku}")
```

The service layer performs this validation before asking the domain model to perform allocation.

The distinction is:

```text
SKU does not exist
        ↓
Application validation
        ↓
InvalidSku
```

versus:

```text
SKU exists
but no batch can satisfy the order
        ↓
Domain rule
        ↓
model.OutOfStock
```

---

# `is_valid_sku()`

```python
def is_valid_sku(sku, batches) -> bool:
```

This function checks whether the requested SKU exists in the current inventory.

It creates a set of SKUs from the available batches:

```python
return sku in {batch.sku for batch in batches}
```

Its responsibility is deliberately small:

> Determine whether the requested SKU exists in the current inventory state.

It does not decide whether the order can actually be fulfilled.

That decision belongs to the domain model.

---

# `allocate()`

```python
def allocate(
    order_line: model.OrderLine,
    uow: unit_of_work.AbstractUnitOfWork,
) -> str:
```

`allocate()` represents the **allocate order line use case**.

It coordinates the entire operation through the Unit of Work.

The flow is:

```text
allocate()
    |
    ↓
uow.batches.list()
    |
    ↓
Validate SKU
    |
    ↓
model.allocate()
    |
    ↓
uow.commit()
    |
    ↓
Return batch reference
```

The service does not directly access a database session or a concrete repository implementation.

Instead, it receives an `AbstractUnitOfWork` that provides the required repository and transaction operations.

---

## Step 1: Retrieve Current State

```python
batches = uow.batches.list()
```

The service asks the Unit of Work for access to the batch repository.

The Unit of Work exposes that repository through:

```python
uow.batches
```

The service then calls:

```python
uow.batches.list()
```

to retrieve the current inventory.

The service does not know whether the repository is backed by SQLAlchemy, an in-memory implementation, or another persistence mechanism.

Conceptually:

```text
Service Layer
      |
      ↓
AbstractUnitOfWork
      |
      ↓
batches repository
      |
      ↓
list()
      |
      ↓
Batch objects
```

This keeps the service layer independent of the concrete persistence technology.

---

## Step 2: Validate the SKU

```python
if not is_valid_sku(order_line.sku, batches):
    raise InvalidSku(f"Invalid sku {order_line.sku}")
```

The service checks whether the requested SKU exists.

If it does not, the use case stops immediately.

```text
Unknown SKU
    ↓
InvalidSku
    ↓
Operation stops
```

---

## Step 3: Delegate Allocation to the Domain

```python
batch_ref = model.allocate(order_line, batches)
```

This is one of the most important lines in the module.

The service layer **does not decide which batch should be used**.

It delegates that decision to the domain model.

The domain model contains the actual allocation rules.

```text
Service Layer
      |
      | model.allocate(...)
      ↓
Domain Model
      |
      ↓
Allocation rules
      |
      ↓
Selected Batch
```

This is an example of keeping responsibilities separated.

---

## Step 4: Commit the Operation

```python
uow.commit()
```

Once allocation succeeds, the service commits the change through the Unit of Work.

The service does not call:

```python
session.commit()
```

because it does not own or directly manage the database session.

The Unit of Work owns the transaction boundary.

Conceptually:

```text
Allocation succeeds
       |
       ↓
uow.commit()
       |
       ↓
Unit of Work
       |
       ↓
Database transaction committed
```

If allocation raises an exception, execution does not reach the commit:

```text
model.allocate()
      |
      ├── Success → uow.commit()
      |
      └── Failure → exception
                     |
                     X
                  no commit
```

The Unit of Work is responsible for the underlying transaction operations.

---

## Step 5: Return the Result

```python
return batch_ref
```

The service returns the reference of the batch that was selected.

The API layer can then transform that result into an HTTP response.

For example:

```text
Domain
   ↓
"batch-001"
   ↓
Service Layer
   ↓
API
   ↓
HTTP response
```

The service layer does not create JSON or Flask responses.

That is the responsibility of the API/entrypoint layer.

---

# Dependency on `AbstractUnitOfWork`

The service function accepts:

```python
uow: unit_of_work.AbstractUnitOfWork
```

rather than a concrete Unit of Work implementation.

This is important because the service layer depends on the **abstraction**, not on a particular persistence technology.

The Unit of Work provides the service with:

```text
AbstractUnitOfWork
       |
       ├── batches
       |
       ├── commit()
       |
       └── rollback()
```

A concrete implementation supplies the actual behavior.

For example:

```text
AbstractUnitOfWork
        |
        └── SQLAlchemyUnitOfWork
                  |
                  ├── SQLAlchemy session
                  |
                  └── SqlAlchemyRepository
```

The service layer does not need to know those implementation details.

---

# Why the Unit of Work Is Used Here

Without a Unit of Work, the service could have to receive several infrastructure dependencies separately:

```text
Service
   |
   ├── Repository
   |
   └── Database Session
```

The Unit of Work groups the persistence-related resources needed by the use case:

```text
Service
   |
   ↓
Unit of Work
   |
   ├── Repository
   |
   └── Transaction
```

This gives the service layer one abstraction through which it can:

```python
uow.batches.list()
uow.commit()
```

rather than directly managing persistence infrastructure.

---

# Testing Benefit

Because the service depends on an abstract Unit of Work, it can be tested without a real database.

Tests can provide a fake implementation:

```text
Service
   ↓
FakeUnitOfWork
   ↓
FakeRepository
   ↓
Python memory
```

Production can provide:

```text
Service
   ↓
SQLAlchemyUnitOfWork
   ↓
SqlAlchemyRepository
   ↓
Database
```

The service function itself does not need to change.

This allows service-layer tests to focus on the behavior of the use case.

For example, a test can verify:

```text
Unknown SKU
    ↓
InvalidSku
```

without needing to create a real production database.

A test can also verify that:

```text
Successful allocation
        ↓
uow.commit()
        ↓
committed == True
```

---

# Service Layer vs Domain Model

These two layers have different responsibilities.

### Domain Model

The domain model answers:

> **What are the business rules?**

For example:

```text
Can this batch allocate this order line?
Which batch should be preferred?
How much inventory is available?
```

### Service Layer

The service layer answers:

> **What steps must happen to perform this use case?**

For example:

```text
Get inventory
    ↓
Validate SKU
    ↓
Call domain
    ↓
Commit
    ↓
Return result
```

Therefore:

```text
Domain Model
    = business decisions

Service Layer
    = application orchestration
```

---

# Service Layer vs Repository

The repository provides access to persistent domain objects.

```text
Repository
    |
    ├── get()
    ├── add()
    └── list()
```

The service layer uses those operations as part of a larger use case.

```text
Service
    |
    ├── uow.batches.list()
    ├── validate
    ├── model.allocate()
    └── uow.commit()
```

The repository does not decide what the application should do.

The service layer coordinates the use case.

The Unit of Work provides the service with access to the repository.

---

# Service Layer vs Unit of Work

These components also have different responsibilities.

### Service Layer

Coordinates the application operation:

```text
Get state
   ↓
Validate
   ↓
Apply domain operation
   ↓
Commit
```

### Unit of Work

Manages the transaction boundary and provides access to repositories:

```text
Unit of Work
   |
   ├── batches repository
   |
   ├── commit()
   |
   └── rollback()
```

Therefore:

```text
Service Layer
    = coordinates the use case

Unit of Work
    = manages the transaction and repository access
```

---

# Service Layer vs API

The API handles communication with external clients.

For example:

```text
HTTP request
     ↓
Parse JSON
     ↓
Call service
     ↓
Receive result
     ↓
Create HTTP response
```

The service layer handles the actual application operation.

Therefore:

```text
API
    = communication

Service Layer
    = use-case orchestration

Domain
    = business rules
```

The API should not contain inventory allocation rules, and the service layer should not contain Flask-specific code.

---

# What This Module Does Not Do

`services.py` does not:

* define domain entities
* define business allocation rules
* decide which batch is preferred
* define database tables
* implement SQLAlchemy mappings
* directly query the database
* directly manage a database session
* handle HTTP requests
* parse JSON
* return Flask responses

Those responsibilities belong elsewhere:

```text
Domain rules
    → domain/model.py

Persistence abstraction
    → adapters/repository.py

Database mapping
    → adapters/orm.py

Transaction management
    → service_layer/unit_of_work.py

HTTP/API
    → entrypoints/
```

---

# The Bigger Architectural Picture

The service layer is where the different architectural components cooperate:

```text
                         API
                          |
                          ↓
                  Service Layer
                          |
                          ↓
                  Abstract Unit of Work
                          |
              ┌───────────┴───────────┐
              ↓                       ↓
         Repository              Transaction
              |                       |
              ↓                       ↓
          Persistence              Commit /
                                  Rollback

                          |
                          ↓
                     Domain Model
                          |
                          ↓
                    Business Rules
```

For the allocation use case:

```text
HTTP request
     |
     ↓
services.allocate()
     |
     ├── uow.batches.list()
     |
     ├── is_valid_sku()
     |
     ├── model.allocate()
     |
     ├── uow.commit()
     |
     └── return batch reference
```

The service layer is therefore the **orchestrator of the use case**, while each component remains responsible for its own concern.

---

# Main Architectural Idea

The most important lesson of the service layer is:

> **A use case should be coordinated in one place without putting all of the business rules in that place.**

The service layer coordinates:

```text
Unit of Work
    +
Domain Model
```

The Unit of Work provides access to persistence and transaction management, while the domain model provides the business decisions.

```text
Service Layer
     |
     ├── "Get the current state."
     │        ↓
     │    Unit of Work
     │        ↓
     │    Repository
     |
     ├── "Apply the business rules."
     │        ↓
     │    Domain Model
     |
     └── "Make the successful operation permanent."
              ↓
          Unit of Work
```

This creates a clear separation:

```text
Domain
→ What the business rules are.

Service Layer
→ What steps make up a use case.

Unit of Work
→ How the use case's transaction and repositories are managed.

Repository
→ How domain objects are accessed.

ORM
→ How domain objects map to database structures.

API
→ How external clients communicate with the application.
```

The service layer is therefore the **application boundary that turns domain capabilities into complete application use cases**.

````

The biggest conceptual change from your old documentation is this:

```text
OLD

Service
   ├── Repository
   └── Session


NEW

Service
   |
   ↓
Unit of Work
   ├── Repository
   └── Transaction/Session
````

So your `services.py` now has **one infrastructure dependency: the Unit of Work**, rather than directly knowing about the repository and database session.
