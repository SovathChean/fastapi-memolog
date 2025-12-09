"""Pytest configuration and fixtures."""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Set test environment before importing app
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"

from app.api.v1.router import router as v1_router
from app.common.constants import API_V1_PREFIX
from app.common.exceptions import register_exception_handlers


def create_test_app() -> FastAPI:
    """Create FastAPI application for testing without database initialization."""
    app = FastAPI(
        title="Test App",
        debug=True,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Include API routers
    app.include_router(v1_router, prefix=API_V1_PREFIX)

    return app


@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    return create_test_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)
