from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.models.base import TimestampMixin


class ProductBase(SQLModel):
    """Campos que a tabela e o contrato da API compartilham."""

    sku: str = Field(max_length=32, unique=True, index=True)
    name: str = Field(max_length=120)
    description: str | None = None
    category: str = Field(max_length=60, index=True)
    price: Decimal = Field(max_digits=12, decimal_places=2)
    weight_kg: Decimal = Field(max_digits=8, decimal_places=3)
    active: bool = True


class Product(ProductBase, TimestampMixin, table=True):
    """Item de catalogo e dono do saldo.

    O saldo vive em dois contadores: o que existe fisicamente e o que ja foi
    prometido. Mantendo isso como coluna -- e nao como soma das movimentacoes --
    da para travar a linha com SELECT FOR UPDATE numa reserva concorrente.
    """

    __tablename__ = "products"
    __table_args__ = (
        # Ultima linha de defesa contra oversell: vale ate para um UPDATE que
        # nao passe pelo service layer.
        CheckConstraint(
            "quantity_reserved <= quantity_on_hand",
            name="ck_products_reserved_within_on_hand",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    quantity_on_hand: int = 0
    quantity_reserved: int = 0

    @property
    def quantity_available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved


class ProductPublic(ProductBase):
    """O que sai nas respostas."""

    id: UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int  # derivado: on_hand - reserved
    created_at: datetime
    updated_at: datetime


class ProductReplenish(SQLModel):
    quantity: int = Field(
        gt=0, description="Unidades que entraram no estoque", schema_extra={"examples": [25]}
    )
