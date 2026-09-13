from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response, status

from app.core.responses import ErrorResponse
from app.models import ReleaseReason, ReservationCreate, ReservationPublic
from app.routers.deps import ReservationServiceDep
from app.services import ReservationLine

router = APIRouter(prefix="/reservations", tags=["reservas"])

# Id fixo no exemplo: o DELETE ja abre apontando para a reserva criada pelo POST.
DEMO_ORDER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

ReservationPath = Path(
    description="Identificador da reserva -- e o proprio order_id do pedido",
    openapi_examples={"demo": {"summary": "Reserva criada pelo exemplo do POST", "value": DEMO_ORDER_ID}},
)


@router.post(
    "",
    response_model=ReservationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Reserva saldo para um pedido",
    description=(
        "Debita o disponivel sem tirar nada da prateleira. O id da reserva e o "
        "proprio `order_id`: um pedido tem no maximo uma reserva.\n\n"
        "**Idempotente por `order_id`:** repetir a chamada com o mesmo pedido "
        "devolve a reserva existente com status **200** em vez de 201, sem "
        "debitar saldo de novo. E o que permite a orders-api fazer retry."
    ),
    responses={
        200: {"model": ReservationPublic, "description": "Reserva ja existia para este order_id"},
        404: {"model": ErrorResponse, "description": "Algum SKU nao existe"},
        409: {"model": ErrorResponse, "description": "Saldo insuficiente, com a lista de faltas"},
        422: {"model": ErrorResponse, "description": "Quantidade invalida"},
    },
)
def create_reservation(
    payload: Annotated[
        ReservationCreate,
        Body(openapi_examples={
            "demo": {
                "summary": "Reserva 2 teclados",
                "value": {"order_id": DEMO_ORDER_ID, "items": [{"sku": "SKU-1042", "quantity": 2}]},
            }
        }),
    ],
    service: ReservationServiceDep,
    response: Response,
) -> ReservationPublic:
    reservation, created = service.reserve(
        order_id=payload.order_id,
        lines=[ReservationLine(sku=i.sku, quantity=i.quantity) for i in payload.items],
        ttl_minutes=payload.ttl_minutes,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return ReservationPublic.from_model(reservation)


@router.delete(
    "/{reservation_id}",
    response_model=ReservationPublic,
    summary="Libera a reserva e devolve o saldo",
    description=(
        "A **compensacao** do fluxo distribuido: quando a orders-api falha "
        "depois de reservar, ela chama esta rota e o saldo volta ao disponivel.\n\n"
        "Idempotente: liberar uma reserva ja liberada nao faz nada."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Reserva inexistente"},
        409: {"model": ErrorResponse, "description": "Reserva ja consumida"},
    },
)
def release_reservation(
    service: ReservationServiceDep,
    reservation_id: UUID = ReservationPath,
    reason: ReleaseReason = Query(
        ReleaseReason.COMPENSATION, description="Por que o saldo esta voltando"
    ),
) -> ReservationPublic:
    return ReservationPublic.from_model(service.release(reservation_id, reason))
