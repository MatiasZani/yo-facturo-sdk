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
    items=[{"descripcion": "Devolución parcial", "cantidad": 1, "precio_unitario": 5000}],
    motivo="Devolución parcial de mercadería",
)
```

## Recursos

- `client.invoices` — comprobantes AFIP/ARCA: `create`, `create_for_customer`, `credit_note`, `debit_note`, `list`, `get`, `authorize`, `cancel`, `supported_types`.
- `client.customers` — `list`, `get`, `create`, `update`, `delete`.
- `client.products` — `list`, `get`, `create`, `update`, `delete`.
- `client.sales` — `list`, `get`, `create`, `update`, `delete`.

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
