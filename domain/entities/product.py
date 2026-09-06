from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Field

from app.db.base import TimestampMixin


class Product(TimestampMixin, table=True):
    __tablename__ = "products"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sku: str = Field(max_length=32, unique=True, index=True)
    name: str = Field(max_length=120)
    description: str | None = None
    category: str = Field(max_length=60, index=True)
    price: Decimal = Field(max_digits=12, decimal_places=2)
    weight_kg: Decimal = Field(max_digits=8, decimal_places=3)
    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    active: bool = True

    @property
    def quantity_available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved
