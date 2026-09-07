from app.routers.health import router as health_router
from app.routers.products import router as products_router
from app.routers.reservations import router as reservations_router

__all__ = ["health_router", "products_router", "reservations_router"]
