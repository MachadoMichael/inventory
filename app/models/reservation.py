from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TimestampMixin
from app.models.enums import ReleaseReason, ReservationStatus


class Reservation(TimestampMixin, table=True):
    """Promessa de saldo para um pedido.

    `order_id` e unico: e essa constraint que torna POST /reservations
    idempotente, para que um retry do client HTTP nao reserve duas vezes.
    """

    __tablename__ = "reservations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(unique=True, index=True)
    status: ReservationStatus = Field(default=ReservationStatus.ACTIVE, index=True)
    release_reason: ReleaseReason | None = None
    requested_by: UUID
    expires_at: datetime = Field(index=True)
    consumed_at: datetime | None = None
    released_at: datetime | None = None

    items: list["ReservationItem"] = Relationship(
        back_populates="reservation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )


# --------------------------------------------------------------- contrato HTTP
# O pedido chega falando em SKU; a tabela guarda product_id. Sao formatos
# genuinamente diferentes, por isso continuam sendo classes proprias.


class ReservationLineIn(SQLModel):
    sku: str = Field(schema_extra={"examples": ["SKU-1042"]})
    quantity: int = Field(gt=0, schema_extra={"examples": [2]})


class ReservationCreate(SQLModel):
    order_id: UUID = Field(
        description="Pedido na orders-api. Repetir o mesmo valor devolve a reserva existente."
    )
    requested_by: UUID = Field(description="Usuario que originou o pedido")
    items: list[ReservationLineIn] = Field(min_length=1)
    ttl_minutes: int | None = Field(
        default=None, gt=0, description="Sobrescreve o prazo padrao da reserva"
    )


class ReservationItemPublic(SQLModel):
    product_id: UUID
    sku: str
    quantity: int


class ReservationPublic(SQLModel):
    id: UUID
    order_id: UUID
    status: ReservationStatus
    release_reason: ReleaseReason | None = None
    requested_by: UUID
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
    released_at: datetime | None = None
    items: list[ReservationItemPublic]

    @classmethod
    def from_model(cls, reservation: Reservation) -> "ReservationPublic":
        return cls(
            id=reservation.id,
            order_id=reservation.order_id,
            status=reservation.status,
            release_reason=reservation.release_reason,
            requested_by=reservation.requested_by,
            created_at=reservation.created_at,
            expires_at=reservation.expires_at,
            consumed_at=reservation.consumed_at,
            released_at=reservation.released_at,
            items=[
                ReservationItemPublic(
                    product_id=item.product_id,
                    sku=item.product.sku,
                    quantity=item.quantity,
                )
                for item in reservation.items
            ],
        )
