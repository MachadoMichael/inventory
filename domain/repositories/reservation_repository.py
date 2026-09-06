from datetime import datetime
from uuid import UUID

from sqlmodel import Session, col, select

from app.models import Reservation, ReservationStatus


class ReservationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, reservation_id: UUID) -> Reservation | None:
        return self.session.get(Reservation, reservation_id)

    def get_by_order_id(self, order_id: UUID) -> Reservation | None:
        """A consulta que sustenta a idempotencia de POST /reservas."""
        return self.session.exec(
            select(Reservation).where(Reservation.order_id == order_id)
        ).first()

    def list_due(self, now: datetime, limit: int = 100) -> list[Reservation]:
        """Reservas ativas que passaram do prazo e devem devolver saldo."""
        stmt = (
            select(Reservation)
            .where(
                Reservation.status == ReservationStatus.ACTIVE,
                Reservation.expires_at < now,
            )
            .order_by(col(Reservation.expires_at))
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    def add(self, reservation: Reservation) -> Reservation:
        self.session.add(reservation)
        return reservation
