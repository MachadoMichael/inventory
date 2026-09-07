from fastapi import APIRouter
from sqlalchemy import text

from app.routers.deps import SessionDep

router = APIRouter(tags=["infra"])


@router.get("/health", summary="Liveness do servico e do banco")
def health(session: SessionDep) -> dict:
    try:
        session.exec(text("SELECT 1"))
        database = "up"
    except Exception:
        database = "down"
    return {
        "service": "inventory-service",
        "status": "ok" if database == "up" else "degraded",
        "database": database,
    }
