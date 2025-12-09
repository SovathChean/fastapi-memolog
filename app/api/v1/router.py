"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.routes import health, user, product, task, telegram

router = APIRouter()

# Include all v1 routes
router.include_router(health.router)
router.include_router(user.router)
router.include_router(product.router)
router.include_router(task.router)
router.include_router(telegram.router)