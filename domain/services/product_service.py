from app.core.exceptions import InvalidQuantity, ProductNotFound
from app.models import MovementType, Product, StockMovement
from app.repositories import MovementRepository, ProductRepository
from sqlmodel import Session


class ProductService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.movements = MovementRepository(session)

    def list_products(
        self,
        *,
        category: str | None = None,
        only_available: bool = False,
        sort: str = "sku",
        descending: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        items = self.products.list(
            category=category,
            only_available=only_available,
            sort=sort,
            descending=descending,
            limit=limit,
            offset=offset,
        )
        total = self.products.count(category=category, only_available=only_available)
        return items, total

    def get_by_sku(self, sku: str) -> Product:
        product = self.products.get_by_sku(sku)
        if product is None:
            raise ProductNotFound([sku])
        return product

    def replenish(self, sku: str, quantity: int) -> Product:
        if quantity <= 0:
            raise InvalidQuantity("a quantidade de reposicao deve ser maior que zero")

        product = self.get_by_sku(sku)
        locked = self.products.lock_by_ids([product.id])[product.id]
        locked.quantity_on_hand += quantity

        self.movements.add(
            StockMovement(
                product_id=locked.id,
                type=MovementType.RECEIPT,
                quantity=quantity,
                balance_after=locked.quantity_on_hand,
            )
        )
        self.session.commit()
        self.session.refresh(locked)
        return locked
