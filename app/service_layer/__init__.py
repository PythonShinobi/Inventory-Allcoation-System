"""
Application service layer for coordinating business use cases.

This package contains the application-level services that coordinate
domain objects, repositories, and transaction management to execute
business use cases.

The service layer sits between the entrypoints of the application and
the domain model. It receives requests from the outside world,
coordinates the required domain operations, and manages interactions
with infrastructure through abstractions.

Architecture::

    Entrypoints
        |
        v
    Service Layer
        |
        +-------------------+
        |                   |
        v                   v
    Domain Model      Unit of Work
                            |
                            v
                       Repository
                            |
                            v
                         Database

The service layer should contain application workflows rather than
low-level persistence or HTTP concerns.

Responsibilities::

    - Coordinate application use cases.
    - Create and pass domain objects to domain logic.
    - Retrieve required data through abstractions.
    - Coordinate transactions through the Unit of Work.
    - Translate domain outcomes into results or application errors.

Non-responsibilities::

    - Defining the core business rules of domain objects.
    - Performing database queries directly.
    - Managing SQLAlchemy sessions directly.
    - Handling HTTP requests or responses.
    - Rendering templates or returning JSON.

The service layer depends on abstractions such as the Unit of Work
rather than concrete infrastructure implementations. This allows the
same application services to be used with different infrastructure
implementations, including test doubles.

For example::

    def allocate(order_line, uow):
        ...

A production application can provide a Unit of Work backed by a real
database, while tests can provide an in-memory implementation without
changing the service itself.
"""