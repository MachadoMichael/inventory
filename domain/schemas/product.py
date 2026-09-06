from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str
    name: str
    description: str | None = None
    category: str
    price: Decimal
    weight_kg: Decimal
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int  # derivado: on_hand - reserved
    active: bool
    created_at: datetime
    updated_at: datetime


class ReplenishRequest(BaseModel):
    quantity: int = Field(gt=0, description="Unidades que entraram no estoque", examples=[25])
