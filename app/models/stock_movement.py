from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.models.base import utcnow
from app.models.enums import MovementType


class StockMovement(SQLModel, table=True):
    __tablename__ = "stock_movements"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(foreign_key="products.id", index=True)
    type: MovementType
    quantity: int  # assinada: negativa em saidas e ajustes para baixo
    reservation_id: UUID | None = Field(default=None, foreign_key="reservations.id")
    balance_after: int  # quantity_on_hand depois desta movimentacao
    created_at: datetime = Field(default_factory=utcnow, index=True)
