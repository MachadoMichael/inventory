from decimal import Decimal

from sqlmodel import Session, select

from app.models import Product

CATALOGO = [
    ("SKU-1042", "Teclado mecanico ABNT2",      "periferico", "349.90", "1.150", 40),
    ("SKU-1088", "Mouse sem fio 2.4GHz",        "periferico", "129.90", "0.320", 120),
    ("SKU-1150", "Headset com microfone",       "periferico", "279.00", "0.480", 25),
    ("SKU-2071", "Monitor 27 polegadas IPS",    "monitor",    "1899.00", "5.400", 8),
    ("SKU-2095", "Monitor 24 polegadas",        "monitor",    "1149.00", "4.100", 15),
    ("SKU-3310", "Cadeira ergonomica",          "mobiliario", "1599.00", "18.700", 6),
    ("SKU-3402", "Suporte articulado para monitor", "mobiliario", "459.00", "3.250", 30),
    ("SKU-4501", "Webcam Full HD",              "periferico", "389.00", "0.210", 0),
]


def seed(session: Session) -> int:
    """Popula o catalogo na primeira subida. Nao faz nada se ja houver produtos."""
    if session.exec(select(Product).limit(1)).first() is not None:
        return 0

    for sku, name, category, price, weight, quantity in CATALOGO:
        session.add(
            Product(
                sku=sku,
                name=name,
                category=category,
                price=Decimal(price),
                weight_kg=Decimal(weight),
                quantity_on_hand=quantity,
            )
        )
    session.commit()
    return len(CATALOGO)
