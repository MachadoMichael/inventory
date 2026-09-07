from dataclasses import dataclass


class InventoryError(Exception):
    """Base dos erros de dominio do estoque."""


class ProductNotFound(InventoryError):
    def __init__(self, skus: list[str]):
        self.skus = skus
        super().__init__(f"produto nao encontrado: {', '.join(skus)}")


class ReservationNotFound(InventoryError):
    def __init__(self, reservation_id):
        self.reservation_id = reservation_id
        super().__init__(f"reserva nao encontrada: {reservation_id}")


@dataclass(frozen=True)
class Shortage:
    sku: str
    requested: int
    available: int


class InsufficientStock(InventoryError):
    """Vira 409 no router, com a lista de faltas no corpo da resposta."""

    def __init__(self, shortages: list[Shortage]):
        self.shortages = shortages
        detalhe = ", ".join(
            f"{s.sku} (pedido {s.requested}, disponivel {s.available})" for s in shortages
        )
        super().__init__(f"saldo insuficiente: {detalhe}")


class ReservationNotActive(InventoryError):
    def __init__(self, reservation_id, status: str, acao: str):
        self.reservation_id = reservation_id
        self.status = status
        super().__init__(f"reserva {reservation_id} esta {status}, nao e possivel {acao}")


class InvalidQuantity(InventoryError):
    def __init__(self, mensagem: str):
        super().__init__(mensagem)
