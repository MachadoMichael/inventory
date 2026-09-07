from collections import defaultdict
from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions import (
    InsufficientStock,
    InvalidQuantity,
    ProductNotFound,
    ReservationNotActive,
    ReservationNotFound,
    Shortage,
)
from app.models.base import utcnow
from app.models import (
    MovementType,
    Product,
    ReleaseReason,
    Reservation,
    ReservationItem,
    ReservationStatus,
    StockMovement,
)
from app.repositories import (
    MovementRepository,
    ProductRepository,
    ReservationRepository,
)
from app.services.dto import ReservationLine


class ReservationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.reservations = ReservationRepository(session)
        self.movements = MovementRepository(session)


    def reserve(
        self,
        *,
        order_id: UUID,
        requested_by: UUID,
        lines: Sequence[ReservationLine],
        ttl_minutes: int | None = None,
    ) -> tuple[Reservation, bool]:
        existing = self.reservations.get_by_order_id(order_id)
        if existing is not None:
            return existing, False

        requested = self._merge(lines)
        products = self._resolve(requested)
        locked = self.products.lock_by_ids([p.id for p in products])
        by_sku = {p.sku: p for p in locked.values()}

        shortages = [
            Shortage(sku=sku, requested=qty, available=by_sku[sku].quantity_available)
            for sku, qty in requested.items()
            if by_sku[sku].quantity_available < qty
        ]
        if shortages:
            raise InsufficientStock(shortages)

        ttl = ttl_minutes if ttl_minutes is not None else settings.reservation_ttl_minutes
        reservation = Reservation(
            order_id=order_id,
            requested_by=requested_by,
            expires_at=utcnow() + timedelta(minutes=ttl),
        )

        for sku, quantity in requested.items():
            product = by_sku[sku]
            product.quantity_reserved += quantity
            reservation.items.append(
                ReservationItem(product_id=product.id, quantity=quantity)
            )
            self._record(product, MovementType.RESERVE, quantity, reservation.id)

        self.reservations.add(reservation)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            winner = self.reservations.get_by_order_id(order_id)
            if winner is None:
                raise
            return winner, False

        self.session.refresh(reservation)
        return reservation, True


    def get(self, reservation_id: UUID) -> Reservation:
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise ReservationNotFound(reservation_id)
        return reservation

    def release(
        self,
        reservation_id: UUID,
        reason: ReleaseReason = ReleaseReason.COMPENSATION,
    ) -> Reservation:
        reservation = self.get(reservation_id)

        if reservation.status is ReservationStatus.RELEASED:
            return reservation  # idempotente: liberar de novo nao faz nada
        if reservation.status is ReservationStatus.CONSUMED:
            raise ReservationNotActive(reservation_id, "CONSUMED", "liberar")

        for item, product in self._locked_items(reservation):
            product.quantity_reserved -= item.quantity
            self._record(product, MovementType.RELEASE, -item.quantity, reservation.id)

        reservation.status = ReservationStatus.RELEASED
        reservation.release_reason = reason
        reservation.released_at = utcnow()

        self.session.commit()
        self.session.refresh(reservation)
        return reservation

    def consume(self, reservation_id: UUID) -> Reservation:
        """Baixa definitiva: a mercadoria saiu."""
        reservation = self.get(reservation_id)

        if reservation.status is ReservationStatus.CONSUMED:
            return reservation
        if reservation.status is ReservationStatus.RELEASED:
            raise ReservationNotActive(reservation_id, "RELEASED", "consumir")

        for item, product in self._locked_items(reservation):
            product.quantity_on_hand -= item.quantity
            product.quantity_reserved -= item.quantity
            self._record(product, MovementType.DISPATCH, -item.quantity, reservation.id)

        reservation.status = ReservationStatus.CONSUMED
        reservation.consumed_at = utcnow()

        self.session.commit()
        self.session.refresh(reservation)
        return reservation

    def expire_due(self, limit: int = 100) -> int:
        due = self.reservations.list_due(utcnow(), limit=limit)
        for reservation in due:
            self.release(reservation.id, ReleaseReason.EXPIRATION)
        return len(due)


    @staticmethod
    def _merge(lines: Sequence[ReservationLine]) -> dict[str, int]:
        if not lines:
            raise InvalidQuantity("a reserva precisa de pelo menos um item")

        merged: dict[str, int] = defaultdict(int)
        for line in lines:
            if line.quantity <= 0:
                raise InvalidQuantity(
                    f"quantidade invalida para {line.sku}: {line.quantity}"
                )
            merged[line.sku] += line.quantity
        return dict(merged)

    def _resolve(self, requested: dict[str, int]) -> list[Product]:
        products = self.products.get_by_skus(list(requested))
        missing = sorted(set(requested) - {p.sku for p in products})
        if missing:
            raise ProductNotFound(missing)
        return products

    def _locked_items(
        self, reservation: Reservation
    ) -> list[tuple[ReservationItem, Product]]:
        locked = self.products.lock_by_ids([i.product_id for i in reservation.items])
        return [(item, locked[item.product_id]) for item in reservation.items]

    def _record(
        self,
        product: Product,
        movement_type: MovementType,
        quantity: int,
        reservation_id: UUID,
    ) -> None:
        self.movements.add(
            StockMovement(
                product_id=product.id,
                type=movement_type,
                quantity=quantity,
                reservation_id=reservation_id,
                balance_after=product.quantity_on_hand,
            )
        )
