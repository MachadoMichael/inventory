from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import ReleaseReason, Reservation, ReservationStatus


class ReservationLineIn(BaseModel):
    sku: str = Field(examples=["SKU-1042"])
    quantity: int = Field(gt=0, examples=[2])


class ReservationCreate(BaseModel):
    order_id: UUID = Field(description="Pedido na orders-api. Repetir o mesmo valor devolve a reserva existente.")
    requested_by: UUID = Field(description="Usuario que originou o pedido")
    items: list[ReservationLineIn] = Field(min_length=1)
    ttl_minutes: int | None = Field(default=None, gt=0, description="Sobrescreve o prazo padrao da reserva")


class ReservationItemRead(BaseModel):
    product_id: UUID
    sku: str
    quantity: int


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    status: ReservationStatus
    release_reason: ReleaseReason | None = None
    requested_by: UUID
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
    released_at: datetime | None = None
    items: list[ReservationItemRead]

    @classmethod
    def from_model(cls, reservation: Reservation) -> Self:
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
                ReservationItemRead(
                    product_id=item.product_id,
                    sku=item.product.sku,
                    quantity=item.quantity,
                )
                for item in reservation.items
            ],
        )
