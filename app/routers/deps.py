from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.database import get_session
from app.services import ProductService, ReservationService

SessionDep = Annotated[Session, Depends(get_session)]


def get_product_service(session: SessionDep) -> ProductService:
    return ProductService(session)


def get_reservation_service(session: SessionDep) -> ReservationService:
    return ReservationService(session)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
ReservationServiceDep = Annotated[ReservationService, Depends(get_reservation_service)]
