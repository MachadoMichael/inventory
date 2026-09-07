from typing import Literal

from fastapi import APIRouter, Path, Query, status

from app.core.pagination import ErrorResponse, Page
from app.models import ProductPublic, ProductReplenish
from app.routers.deps import ProductServiceDep

router = APIRouter(prefix="/products", tags=["produtos"])

SkuPath = Path(description="Codigo do produto", examples=["SKU-1042"])


@router.get(
    "",
    response_model=Page[ProductPublic],
    summary="Lista o catalogo",
    description="Paginado, com filtro por categoria e por disponibilidade, "
    "e ordenacao por um conjunto fechado de campos.",
)
def list_products(
    service: ProductServiceDep,
    category: str | None = Query(None, description="Filtra por categoria", examples=["periferico"]),
    available: bool = Query(False, description="Apenas produtos com saldo disponivel"),
    sort: Literal["sku", "name", "price", "quantity_on_hand", "created_at"] = "sku",
    order: Literal["asc", "desc"] = "asc",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[ProductPublic]:
    items, total = service.list_products(
        category=category,
        only_available=available,
        sort=sort,
        descending=(order == "desc"),
        limit=limit,
        offset=offset,
    )
    return Page[ProductPublic](
        items=[ProductPublic.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{sku}",
    response_model=ProductPublic,
    summary="Detalha um produto",
    description="Traz o saldo fisico, o reservado e o disponivel para venda.",
    responses={404: {"model": ErrorResponse, "description": "SKU inexistente"}},
)
def get_product(service: ProductServiceDep, sku: str = SkuPath) -> ProductPublic:
    return ProductPublic.model_validate(service.get_by_sku(sku))


@router.post(
    "/{sku}/replenishments",
    response_model=ProductPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registra entrada de estoque",
    description="Aumenta o saldo fisico e grava a movimentacao no razao.",
    responses={
        404: {"model": ErrorResponse, "description": "SKU inexistente"},
        422: {"model": ErrorResponse, "description": "Quantidade invalida"},
    },
)
def replenish(
    payload: ProductReplenish,
    service: ProductServiceDep,
    sku: str = SkuPath,
) -> ProductPublic:
    return ProductPublic.model_validate(service.replenish(sku, payload.quantity))
