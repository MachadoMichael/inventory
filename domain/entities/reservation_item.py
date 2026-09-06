from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from app.models.product import Product
from app.models.reservation import Reservation


class ReservationItem(SQLModel, table=True):
    __tablename__ = "reservation_items"

    reservation_id: UUID = Field(foreign_key="reservations.id", primary_key=True)
    product_id: UUID = Field(foreign_key="products.id", primary_key=True)
    quantity: int

    reservation: Reservation = Relationship(back_populates="items")
    product: Product = Relationship(sa_relationship_kwargs={"lazy": "selectin"})
