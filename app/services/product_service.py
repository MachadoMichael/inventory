from app.core.exceptions import ProductNotFound
from app.models import Product
from app.repositories import ProductRepository
from sqlmodel import Session


class ProductService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)

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
