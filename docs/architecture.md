# Architecture

## Overview

The system separates business logic from infrastructure concerns.

HTTP requests enter through the API layer.

The Service Layer coordinates application use cases.

The Domain Model contains business rules.

Repositories provide an abstraction over persistence.

The ORM maps domain objects to database structures.

## Dependency Direction

API
 ↓
Service Layer
 ↓
Domain Model

Service Layer
 ↓
Repository Port
 ↓
Repository Adapter
 ↓
Database
