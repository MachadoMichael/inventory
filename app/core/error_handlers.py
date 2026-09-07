from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    InsufficientStock,
    InvalidQuantity,
    ProductNotFound,
    ReservationNotActive,
    ReservationNotFound,
)


def _error(code: str, status_code: int, message: str, details=None) -> JSONResponse:
    body: dict = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    """Traduz os erros de dominio em respostas HTTP consistentes.

    Nenhuma excecao vaza como stacktrace: a orders-api sempre recebe um corpo
    JSON que consegue interpretar.
    """

    @app.exception_handler(ProductNotFound)
    async def _product_not_found(request: Request, exc: ProductNotFound):
        return _error("PRODUCT_NOT_FOUND", status.HTTP_404_NOT_FOUND, str(exc),
                      [{"sku": sku} for sku in exc.skus])

    @app.exception_handler(ReservationNotFound)
    async def _reservation_not_found(request: Request, exc: ReservationNotFound):
        return _error("RESERVATION_NOT_FOUND", status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(InsufficientStock)
    async def _insufficient_stock(request: Request, exc: InsufficientStock):
        return _error(
            "INSUFFICIENT_STOCK",
            status.HTTP_409_CONFLICT,
            str(exc),
            [
                {"sku": s.sku, "requested": s.requested, "available": s.available}
                for s in exc.shortages
            ],
        )

    @app.exception_handler(ReservationNotActive)
    async def _reservation_not_active(request: Request, exc: ReservationNotActive):
        return _error("RESERVATION_NOT_ACTIVE", status.HTTP_409_CONFLICT, str(exc),
                      [{"status": exc.status}])

    @app.exception_handler(InvalidQuantity)
    async def _invalid_quantity(request: Request, exc: InvalidQuantity):
        return _error("INVALID_QUANTITY", status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
