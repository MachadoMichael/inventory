from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.db.base import TimestampMixin
from app.models.enums import ReleaseReason, ReservationStatus


class Reservation(TimestampMixin, table=True):
    __tablename__ = "reservations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(unique=True, index=True)  # torna a reserva idempotente
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
