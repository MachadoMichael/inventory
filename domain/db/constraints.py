from sqlalchemy import CheckConstraint

from app.models.product import Product

OVERSELL = CheckConstraint(
    "quantity_reserved <= quantity_on_hand",
    name="ck_products_reserved_within_on_hand",
)


def register() -> None:
    table = Product.__table__
    if not any(c.name == OVERSELL.name for c in table.constraints):
        table.append_constraint(OVERSELL)
