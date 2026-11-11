# yofacturo (Python)

SDK oficial de Python para la [API de YoFacturo](https://yo-facturo.com/dev/) — facturación electrónica ARCA/AFIP para Argentina, catálogo, ventas y clientes, de forma programática.

Sin dependencias externas (usa `urllib` de la librería estándar). Python 3.8+.

## Instalación

```bash
pip install yofacturo
```

O desde este repo, en modo editable:

```bash
pip install -e "python[dev]"
```

## Uso

```python
from yofacturo import YoFacturo

client = YoFacturo(api_key="yf_live_...")  # Configuración → Integraciones → API Tokens

# Emitir una factura (autorizar=True dispara el CAE en segundo plano)
factura = client.invoices.create(
    punto_venta=1,
    tipo_documento=99,
    numero_documento="0",
    razon_social="CONSUMIDOR FINAL",
    items=[{"descripcion": "Servicio de consultoría", "cantidad": 1, "precio_unitario": 15000}],
    autorizar=True,
)
print(factura["data"]["id"])

# Listar comprobantes
comprobantes = client.invoices.list(page=1, per_page=20, estado="aprobado")

# Emitir una nota de crédito asociada
nota = client.invoices.credit_note(
    factura["data"]["id"],
    lineas=[{"linea": 0, "cantidad": 1}],  # 1 unidad del primer renglón (o importe_a_acreditar= / porcentaje_aplicar=)
    motivo="Devolución parcial de mercadería",
)
```

## Agent quickstart (English)

Issue an ARCA/AFIP e-invoice from an AI agent or a script in four steps. Docs: <https://yo-facturo.com/dev/>.

```bash
pip install yofacturo            # add "yofacturo[keyring]" to store the token in the OS keyring
export YOFACTURO_API_KEY=yf_test_...   # sandbox key (no ARCA, synthetic CAE); yf_live_... for real invoices
yofacturo login                  # verifies the token; the key is never echoed or taken from argv
yofacturo invoice create -f invoice.json --idempotency-key "order-1234"
yofacturo invoice get <id>       # poll until "cae" is set, or read "afip_errors" on a rejection
yofacturo invoice link <id>      # signed public URL (PDF/HTML) to share with the customer
yofacturo webhooks verify --secret-env YF_WEBHOOK_SECRET --payload-file body.raw --signature "t=...,v1=..."
```

Every command prints one JSON document on stdout: `{"ok": true, "data": ...}` or, on failure,
`{"ok": false, "error": {"kind", "message", "status", "code", "afip_errors"...}}` with a non-zero exit code
(1 API error / invalid signature, 2 bad usage or input, 3 missing token). `--environment testing` adds
`"ambiente": "testing"` to the request bodies (ARCA homologation with a live key; a `yf_test_` key does not need it).

Same helpers from Python:

```python
from yofacturo import YoFacturo, webhooks, is_sandbox_key

client = YoFacturo(api_key="yf_live_...", environment="testing")  # sends "ambiente": "testing"
client.is_sandbox                       # True for yf_test_ keys
client.invoices.create(idempotency_key="order-1234", **payload)   # Idempotency-Key header: safe retries
client.invoices.link(invoice_id)        # POST /bill/receipts/{id}/public-link/

# In your webhook endpoint, verify the RAW body (not re-serialized JSON):
event = webhooks.construct_event(secret, raw_body, request.headers["X-YF-Signature"])  # ValueError if invalid
```

Signature scheme: `X-YF-Signature: t=<unix_ts>,v1=<hex>`, `hex = HMAC_SHA256(secret, "<t>." + raw_body)`,
constant-time comparison, 300 s replay tolerance.

## Resumen en español

`pip install yofacturo` instala la librería y el comando `yofacturo` (salida siempre JSON, pensado para agentes).
El token se lee de `YOFACTURO_API_KEY` (o del keyring con `yofacturo[keyring]` y `yofacturo login --store`), nunca por
argumentos. Tokens `yf_test_` = sandbox (CAE sintético); con un token `yf_live_` podés homologar contra ARCA con
`--environment testing`. `idempotency_key=` evita duplicar comprobantes al reintentar, y `webhooks.verify_signature`
valida la firma `X-YF-Signature` de las entregas.

## Recursos

- `client.invoices` — comprobantes AFIP/ARCA: `create`, `create_for_customer`, `credit_note`, `debit_note`, `list`, `get`, `authorize`, `cancel`, `supported_types`.
- `client.customers` — `list`, `get`, `create`, `update`, `delete`.
- `client.products` — `list`, `get`, `create`, `update`, `delete`. `list` manda `currency_aware=1` por defecto (productos con `price_currency` en otra moneda, ej. USD; `currency_aware=False` lo desactiva); al vender esos productos mandá `currency` en `sales.create`.
- `client.sales` — `list`, `get`, `create`, `update`, `delete`.
- `client.services`, `client.rentals` — `list`, `get`, `create`, `update`, `delete` (scopes `services:*` / `rentals:*`). `list` manda `currency_aware=1` por defecto, igual que `products` (`currency_aware=False` lo desactiva).
- `client.appointments`, `client.subscription_plans` — `list`, `get`, `create`, `update`, `delete` (scopes `appointments:*` / `recurring:*`).

## Manejo de errores

```python
from yofacturo import (
    AuthenticationError,   # 401
    ScopeError,            # 403 (alias: PermissionError)
    NotFoundError,         # 404
    ValidationError,       # 400 / 422 (trae .errors con el detalle por campo)
    RateLimitError,        # 429 (trae .retry_after si la API lo informó)
    ApiError,              # catch-all
)

try:
    client.invoices.authorize(comprobante_id)
except ValidationError as exc:
    print(exc.code, exc.errors)
except RateLimitError as exc:
    print("esperar", exc.retry_after, "segundos")
```

El cliente reintenta automáticamente (backoff exponencial, hasta 3 veces por defecto) ante `429` y `5xx`. Configurable con `YoFacturo(max_retries=...)`.

## Tests

```bash
pip install -e "python[dev]"
pytest
```

Los tests no usan red: inyectan un transporte falso (`YoFacturo(transport=...)`).

## Links

- Documentación: https://yo-facturo.com/dev/
- Spec OpenAPI: https://api.yo-facturo.com/api/v1/openapi.json
- Estado del servicio: https://status.yo-facturo.com
