from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.core.error_handlers import register_error_handlers
from app.seed import seed
from app.database import engine, init_db
from app.routers import health_router, products_router, reservations_router

TAGS = [
    {
        "name": "produtos",
        "description": "Catalogo e saldo. O saldo vive em dois contadores: "
        "**on_hand** (o que existe fisicamente) e **reserved** (o que ja foi "
        "prometido). O disponivel para venda e a diferenca entre os dois.",
    },
    {
        "name": "reservas",
        "description": "Ciclo de vida da promessa de saldo: **reservar**, "
        "**liberar** (a compensacao) e **consumir** (a saida definitiva).",
    },
    {"name": "infra", "description": "Liveness."},
]

DESCRIPTION = """
Servico de estoque do MVP de microsservicos.

E o **dono do saldo**: nenhum outro servico escreve na tabela de produtos.
A orders-api pergunta por HTTP se ha saldo antes de confirmar um pedido, e
desfaz a reserva por esta mesma API se a etapa seguinte falhar.

**Garantias**

* `POST /reservations` e idempotente por `order_id` -- retry nao reserva duas vezes.
* Reservas concorrentes travam a linha do produto com `SELECT ... FOR UPDATE`,
  sempre na mesma ordem, para nao dar deadlock.
* Toda mudanca de saldo deixa rastro em `stock_movements` com a causa.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        criados = seed(session)
        if criados:
            print(f"[seed] {criados} produtos inseridos no catalogo")
    yield


app = FastAPI(
    title="Inventory Service",
    description=DESCRIPTION,
    version="0.1.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

register_error_handlers(app)
app.include_router(health_router)
app.include_router(products_router)
app.include_router(reservations_router)
