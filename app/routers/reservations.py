from uuid import UUID

from fastapi import APIRouter, Path, Query, Response, status

from app.core.pagination import ErrorResponse
from app.models import ReleaseReason, ReservationCreate, ReservationPublic
from app.routers.deps import ReservationServiceDep
from app.services import ReservationLine

router = APIRouter(prefix="/reservations", tags=["reservas"])

ReservationPath = Path(description="Identificador da reserva")


@router.post(
    "",
    response_model=ReservationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Reserva saldo para um pedido",
    description=(
        "Debita o disponivel sem tirar nada da prateleira.\n\n"
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
    payload: ReservationCreate,
    service: ReservationServiceDep,
    response: Response,
) -> ReservationPublic:
    reservation, created = service.reserve(
        order_id=payload.order_id,
        requested_by=payload.requested_by,
        lines=[ReservationLine(sku=i.sku, quantity=i.quantity) for i in payload.items],
        ttl_minutes=payload.ttl_minutes,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return ReservationPublic.from_model(reservation)


@router.get(
    "/{reservation_id}",
    response_model=ReservationPublic,
    summary="Consulta uma reserva",
    responses={404: {"model": ErrorResponse, "description": "Reserva inexistente"}},
)
def get_reservation(
    service: ReservationServiceDep,
    reservation_id: UUID = ReservationPath,
) -> ReservationPublic:
    return ReservationPublic.from_model(service.get(reservation_id))


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


@router.post(
    "/{reservation_id}/consumption",
    response_model=ReservationPublic,
    summary="Confirma a saida da mercadoria",
    description="Baixa definitiva: reduz o saldo fisico e encerra a reserva.",
    responses={
        404: {"model": ErrorResponse, "description": "Reserva inexistente"},
        409: {"model": ErrorResponse, "description": "Reserva ja liberada"},
    },
)
def consume_reservation(
    service: ReservationServiceDep,
    reservation_id: UUID = ReservationPath,
) -> ReservationPublic:
    return ReservationPublic.from_model(service.consume(reservation_id))
