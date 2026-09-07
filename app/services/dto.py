from dataclasses import dataclass


@dataclass(frozen=True)
class ReservationLine:
    sku: str
    quantity: int
