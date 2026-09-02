
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
     ├── Repository
     |
     ├── Domain Model
     |
     └── Database Session
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
    ├── Get inventory
    |
    ├── Validate SKU
    |
    ├── Ask domain to allocate
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
          ┌───────────┼───────────┐
          ↓           ↓           ↓
     Repository    Domain      Session
          |           |           |
          ↓           ↓           ↓
      Database     Business    Transaction
                   Rules
```

The API should not need to know how inventory allocation works.

The domain should not need to know how HTTP requests or database sessions work.

The service layer coordinates these components.

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
    repo: AbstractRepository,
    session,
) -> str:
```

`allocate()` represents the **allocate order line use case**.

It coordinates the entire operation.

The flow is:

```text
allocate()
    |
    ↓
repo.list()
    |
    ↓
Validate SKU
    |
    ↓
model.allocate()
    |
    ↓
session.commit()
    |
    ↓
Return batch reference
```

---

## Step 1: Retrieve Current State

```python
batches = repo.list()
```

The service layer asks the repository for the current inventory.

It does not query the database directly.

Instead of:

```python
session.query(...)
```

the service uses:

```python
repo.list()
```

This keeps the service layer independent of the concrete persistence mechanism.

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
session.commit()
```

Once allocation succeeds, the service commits the change.

Conceptually:

```text
Allocation succeeds
       |
       ↓
Commit transaction
```

If allocation raises an exception, execution does not reach the commit:

```text
model.allocate()
      |
      ├── Success → commit()
      |
      └── Failure → exception
                     |
                     X
                  no commit
```

This helps ensure that unsuccessful operations are not committed.

The broader responsibility for transaction boundaries is eventually handled through the **Unit of Work** pattern.

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

# Dependency on `AbstractRepository`

The function accepts:

```python
repo: AbstractRepository
```

rather than:

```python
repo: SqlAlchemyRepository
```

This is important.

The service layer depends on the **repository abstraction** rather than a specific implementation.

Therefore:

```text
                  Service
                     |
                     ↓
           AbstractRepository
                /          \
               /            \
              ↓              ↓
      SQLAlchemyRepo      FakeRepository
              |              |
              ↓              ↓
          Database         Memory
```

The same service function can therefore operate with either implementation.

---

# Testing Benefit

Because the service depends on an abstraction, it can be tested without a real database.

For example:

```text
Service
   ↓
FakeRepository
   ↓
Python memory
```

Instead of:

```text
Service
   ↓
SQLAlchemyRepository
   ↓
SQLAlchemy
   ↓
Database
```

This allows service-layer tests to focus on the behavior of the use case.

For example, a test can verify:

```text
Unknown SKU
    ↓
InvalidSku
```

without needing to create a real production database.

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
    ├── repo.list()
    ├── validate
    ├── model.allocate()
    └── commit
```

The repository does not decide what the application should do.

The service layer coordinates the use case.

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
              ┌───────────┼───────────┐
              ↓           ↓           ↓
         Repository     Domain      Session
              |           |           |
              ↓           ↓           ↓
          Persistence   Business    Transaction
                         Rules
```

For the allocation use case:

```text
HTTP request
     |
     ↓
services.allocate()
     |
     ├── repo.list()
     |
     ├── is_valid_sku()
     |
     ├── model.allocate()
     |
     ├── session.commit()
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
Repository
    +
Domain Model
    +
Transaction
```

but delegates each responsibility to the appropriate component.

```text
Service Layer
     |
     ├── "Get the current state."
     │        ↓
     │    Repository
     |
     ├── "Apply the business rules."
     │        ↓
     │    Domain Model
     |
     └── "Make the successful operation permanent."
              ↓
          Transaction
```

This creates a clear separation:

```text
Domain
→ What the business rules are.

Service Layer
→ What steps make up a use case.

Repository
→ How domain objects are accessed.

ORM
→ How domain objects map to database structures.

API
→ How external clients communicate with the application.
```

The service layer is therefore the **application boundary that turns domain capabilities into complete application use cases**.
