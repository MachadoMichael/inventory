from sqlalchemy import CheckConstraint

from app.models.product import Product

# Ultima linha de defesa contra oversell: vale mesmo para um UPDATE que nao
# passe pelo service layer (seed, correcao manual, corrida entre transacoes).
OVERSELL = CheckConstraint(
    "quantity_reserved <= quantity_on_hand",
    name="ck_products_reserved_within_on_hand",
)


def register() -> None:
    table = Product.__table__
    if not any(c.name == OVERSELL.name for c in table.constraints):
        table.append_constraint(OVERSELL)
