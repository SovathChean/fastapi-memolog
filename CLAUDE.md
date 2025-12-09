# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development server (hot reload)
fastapi dev main.py

# Production server
fastapi run main.py

# Run tests
pytest

# Run unit tests only
pytest tests/unit -v

# Run integration tests only
pytest tests/integration -v

# Run single test
pytest tests/unit/services/test_hello_service.py::test_create_greeting_success -v

# Lint
ruff check .

# Format
ruff format .

# Install dependencies
pip install -r requirements-dev.txt
```

## Architecture

This is a layered FastAPI template with 7 distinct layers:

```
fastapi-template/
├── app/                      # Main application package
│   ├── api/                  # Routes + Controllers
│   │   ├── deps.py           # Shared dependencies
│   │   └── v1/
│   │       ├── router.py     # V1 router aggregator
│   │       ├── routes/       # Endpoint definitions
│   │       └── controllers/  # Request/response handlers
│   ├── services/             # Business logic layer
│   ├── support/              # Complex reusable logic
│   ├── models/
│   │   ├── schemas/          # Pydantic API models
│   │   └── domain/           # SQLAlchemy ORM models
│   ├── repositories/         # Data access layer
│   ├── common/               # Utils, exceptions, constants
│   └── main.py               # App factory
├── config/                   # Configuration package
│   ├── settings.py           # Pydantic settings
│   └── database.py           # SQLAlchemy async setup
├── tests/                    # Test package
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
└── main.py                   # Entry point
```

## Layer Responsibilities

| Layer | Purpose | Location |
|-------|---------|----------|
| **Route** | Define endpoints, declare schemas | `app/api/v1/routes/` |
| **Controller** | Handle HTTP request/response | `app/api/v1/controllers/` |
| **Service** | Business logic | `app/services/` |
| **Support** | Complex shared logic | `app/support/` |
| **Model** | Data structures | `app/models/` |
| **Repository** | Data access | `app/repositories/` |
| **Common** | Utilities | `app/common/` |

## Dependency Flow

```
Request → Route → Controller → Service → Repository
                      ↓              ↓
                   Models       Support
```

## Environment Setup

1. Copy `.env.dev` or `.env.production` to `.env`
2. Ensure PostgreSQL is running
3. Update `DATABASE_URL` in `.env` if needed

## Key Patterns

- **Dependency Injection**: Use `Depends()` for services, controllers, settings
- **Async**: All endpoints and database operations are async
- **API Versioning**: Routes are versioned under `/api/v1/`
- **Repository Pattern**: Data access abstracted through repositories
- **Service Layer**: Business logic isolated from HTTP concerns

## Database

Uses SQLAlchemy async with asyncpg driver:

```python
from config.database import get_db
from app.api.deps import DbSessionDep

# In route handlers
async def my_route(db: DbSessionDep):
    ...
```

## Adding New Features

1. Create schema in `app/models/schemas/`
2. Create repository in `app/repositories/`
3. Create support module if needed in `app/support/`
4. Create service in `app/services/`
5. Create controller in `app/api/v1/controllers/`
6. Create routes in `app/api/v1/routes/`
7. Include router in `app/api/v1/router.py`
