# inventory-service — API secundária de estoque

Serviço de **estoque** do MVP de microsserviços. É o **dono do saldo**: nenhum outro
serviço escreve na tabela de produtos. A `orders-api` pergunta por HTTP se há saldo
antes de confirmar um pedido, e desfaz a reserva por esta mesma API se a etapa
seguinte do fluxo falhar.

Faz parte de um sistema de três módulos:

| Módulo | Repositório | Porta |
|---|---|---|
| orders-api (principal) | https://github.com/MachadoMichael/order | 8000 |
| **inventory-service** (este) | https://github.com/MachadoMichael/inventory | 8001 |
| delivery-service | https://github.com/MachadoMichael/delivery | 8002 |

O diagrama da arquitetura está no README do repositório principal.

---

## O modelo de saldo

O saldo vive em **dois contadores**, não um:

| Campo | Significado |
|---|---|
| `quantity_on_hand` | O que existe fisicamente na prateleira |
| `quantity_reserved` | O que já foi prometido a algum pedido |
| `quantity_available` | A diferença entre os dois — o que ainda dá para vender |

Essa separação é o que dá sentido à reserva: **reservar move do disponível para o
reservado sem tirar nada da prateleira.** Liberar desfaz. Despachar aí sim baixa o
saldo físico.

### Ciclo de vida da reserva

```
                    ┌─── CONSUMED    (a mercadoria saiu)
   ACTIVE ──────────┤
                    └─── RELEASED    (o saldo voltou ao disponível)
```

Uma reserva liberada sempre registra o **motivo**: `COMPENSATION` (a orders-api
desfez após falha na cotação do frete), `ORDER_CANCELLED` ou `EXPIRATION`.

### Garantias

- **Idempotência.** `POST /reservations` é único por `order_id`. Chamar duas vezes
  para o mesmo pedido devolve a mesma reserva com HTTP **200** em vez de 201, sem
  debitar saldo de novo — é o que permite a `orders-api` fazer *retry* sem medo.
- **Concorrência.** A reserva trava a linha do produto com `SELECT ... FOR UPDATE`,
  **sempre na ordem do id**, para que duas reservas simultâneas sobre os mesmos
  produtos não deem *deadlock*.
- **Integridade no banco.** A constraint `quantity_reserved <= quantity_on_hand`
  recusa o *oversell* mesmo que a lógica da aplicação falhe.
- **Auditoria.** Toda mudança de saldo grava uma linha em `stock_movements` com o
  tipo, a quantidade e a reserva que a causou.

---

## Como executar

### Junto com o sistema completo (recomendado)

O `docker-compose.yml` que sobe os três serviços fica no repositório da
**orders-api**. Siga as instruções de lá.

### Isolado

Este serviço é autônomo e roda sozinho, precisando apenas de um PostgreSQL.

**Pré-requisitos:** Docker, ou Python 3.12+ e um PostgreSQL acessível.

```bash
# Com Docker
docker build -t inventory-service .
docker run --rm -p 8001:8001 \
  -e DATABASE_URL="postgresql+psycopg://mvp:mvp@host.docker.internal:5432/inventory_db" \
  inventory-service

# Localmente
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite:///./inventory.db"     # SQLite também funciona
uvicorn app.main:app --reload --port 8001
```

Na primeira execução as tabelas são criadas e o catálogo é populado com 8 produtos.

- **Swagger:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc
- **Health:** http://localhost:8001/health

---

## Rotas

### Produtos

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/products` | Catálogo paginado, com `?category=`, `?available=true`, `?sort=`, `?order=`, `?limit=`, `?offset=` |
| `GET` | `/products/{sku}` | Saldo físico, reservado e disponível |
| `POST` | `/products/{sku}/replenishments` | Entrada de estoque, registrada no razão |

### Reservas

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/reservations` | **Reserva saldo.** Idempotente por `order_id` |
| `GET` | `/reservations/{id}` | Estado da reserva e seus itens |
| `DELETE` | `/reservations/{id}` | **Compensação:** libera e devolve o saldo. Aceita `?reason=` |
| `POST` | `/reservations/{id}/consumption` | Baixa definitiva: a mercadoria saiu |

### Infra

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Liveness do serviço e do banco |

### Erros

| Código | HTTP | Quando |
|---|---|---|
| `PRODUCT_NOT_FOUND` | 404 | SKU fora do catálogo |
| `RESERVATION_NOT_FOUND` | 404 | Reserva inexistente |
| `INSUFFICIENT_STOCK` | 409 | Saldo insuficiente, **com a lista de faltas** |
| `RESERVATION_NOT_ACTIVE` | 409 | Operação incompatível com o status |
| `INVALID_QUANTITY` | 422 | Quantidade menor ou igual a zero |

```json
{
  "code": "INSUFFICIENT_STOCK",
  "message": "saldo insuficiente: SKU-2071 (pedido 50, disponivel 7)",
  "details": [{ "sku": "SKU-2071", "requested": 50, "available": 7 }]
}
```

---

## Exemplos

```bash
# Catálogo filtrado e ordenado
curl "localhost:8001/products?category=periferico&sort=price&order=desc&limit=3"

# Só o que tem saldo
curl "localhost:8001/products?available=true"

# Reservar
curl -X POST localhost:8001/reservations -H 'Content-Type: application/json' -d '{
  "order_id": "11111111-1111-1111-1111-111111111111",
  "requested_by": "22222222-2222-2222-2222-222222222222",
  "items": [{"sku": "SKU-1042", "quantity": 2}]
}'
#   -> 201 na primeira vez, 200 nas seguintes (mesma reserva, saldo intacto)

# Compensar
curl -X DELETE "localhost:8001/reservations/{id}?reason=COMPENSATION"
#   -> o saldo volta ao disponível

# Entrada de estoque
curl -X POST localhost:8001/products/SKU-4501/replenishments \
  -H 'Content-Type: application/json' -d '{"quantity": 25}'
```

---

## Variáveis de ambiente

Veja `.env.example`.

| Variável | Padrão | Para quê |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://mvp:mvp@postgres:5432/inventory_db` | Conexão com o banco |
| `RESERVATION_TTL_MINUTES` | `15` | Prazo antes de a reserva poder expirar |
| `ECHO_SQL` | `false` | Loga o SQL gerado |

---

## Estrutura do projeto

```
inventory/
├── Dockerfile
└── app/
    ├── main.py
    ├── database.py      engine, sessão e criação do schema
    ├── seed.py          catálogo inicial
    ├── core/            config, exceptions, error_handlers,
    │                    responses (Page[T], ErrorResponse)
    ├── models/          Product, Reservation, ReservationItem, StockMovement
    ├── repositories/    acesso a dados, paginação, SELECT FOR UPDATE
    ├── services/        regra de negócio: reserva, liberação, consumo
    └── routers/         products, reservations, health
```

Cada arquivo de `models/` traz a tabela **e** o contrato HTTP correspondente —
`ProductBase`, `Product` (a tabela) e `ProductPublic`. É o padrão do SQLModel:
um campo declarado uma vez só, servindo de ORM, validação e schema do Swagger.

## Stack

Python 3.12 · FastAPI · SQLModel · PostgreSQL 16 · Docker
