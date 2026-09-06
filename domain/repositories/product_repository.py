from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select

from app.models import Product

# Whitelist de ordenacao: o valor vindo da querystring nunca entra na SQL.
SORTABLE = {
    "sku": Product.sku,
    "name": Product.name,
    "price": Product.price,
    "quantity_on_hand": Product.quantity_on_hand,
    "created_at": Product.created_at,
}


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, product_id: UUID) -> Product | None:
        return self.session.get(Product, product_id)

    def get_by_sku(self, sku: str) -> Product | None:
        return self.session.exec(select(Product).where(Product.sku == sku)).first()

    def get_by_skus(self, skus: Sequence[str]) -> list[Product]:
        if not skus:
            return []
        return list(self.session.exec(select(Product).where(col(Product.sku).in_(skus))).all())

    def lock_by_ids(self, product_ids: Sequence[UUID]) -> dict[UUID, Product]:
        """Carrega os produtos com SELECT ... FOR UPDATE.

        A ordenacao por id e deliberada: duas reservas concorrentes que tocam
        os mesmos produtos travam sempre na mesma sequencia e nao deadlockam.
        """
        if not product_ids:
            return {}
        stmt = (
            select(Product)
            .where(col(Product.id).in_(product_ids))
            .order_by(col(Product.id))
            .with_for_update()
        )
        return {p.id: p for p in self.session.exec(stmt).all()}

    def list(
        self,
        *,
        category: str | None = None,
        only_available: bool = False,
        active_only: bool = True,
        sort: str = "sku",
        descending: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Product]:
        column = SORTABLE.get(sort, Product.sku)
        order = col(column).desc() if descending else col(column).asc()
        stmt = (
            select(Product)
            .where(*self._filters(category, only_available, active_only))
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.exec(stmt).all())

    def count(
        self,
        *,
        category: str | None = None,
        only_available: bool = False,
        active_only: bool = True,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(*self._filters(category, only_available, active_only))
        )
        return self.session.exec(stmt).one()

    def add(self, product: Product) -> Product:
        self.session.add(product)
        return product

    @staticmethod
    def _filters(
        category: str | None, only_available: bool, active_only: bool
    ) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = []
        if category:
            clauses.append(Product.category == category)
        if active_only:
            clauses.append(col(Product.active).is_(True))
        if only_available:
            clauses.append(Product.quantity_on_hand - Product.quantity_reserved > 0)
        return clauses
