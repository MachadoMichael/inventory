from uuid import UUID

from sqlmodel import Session, col, select

from app.models import StockMovement


class MovementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, movement: StockMovement) -> StockMovement:
        self.session.add(movement)
        return movement

    def list_by_product(
        self, product_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[StockMovement]:
        stmt = (
            select(StockMovement)
            .where(StockMovement.product_id == product_id)
            .order_by(col(StockMovement.created_at).desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.exec(stmt).all())
