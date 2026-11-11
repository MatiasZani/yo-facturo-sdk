# SDKs de YoFacturo

SDKs oficiales para la **API de facturación electrónica ARCA (ex AFIP) de Argentina** de [YoFacturo](https://yo-facturo.com): emití facturas, notas de crédito y notas de débito con CAE, y manejá tu catálogo, tus ventas y tus clientes de forma programática, desde tu ERP, tu e-commerce o tus propios sistemas.

| SDK | Paquete | Estado |
|---|---|---|
| Python | [`python/`](python/) — `yofacturo` | ![tests](https://img.shields.io/badge/tests-passing-brightgreen) |
| Node.js / TypeScript | [`node/`](node/) — `yofacturo` | ![tests](https://img.shields.io/badge/tests-passing-brightgreen) |
| PHP | [`php/`](php/) — `yofacturo/yofacturo-php` | PSR-4, sin dependencias |

También incluye la [spec OpenAPI 3.1](openapi/) completa y una [colección de Postman](postman/) con las 236 operaciones de la API, agrupadas por área.

## ¿Qué es la API de YoFacturo?

Una API REST sobre HTTPS que te permite operar tu cuenta de YoFacturo por código: emitir comprobantes electrónicos AFIP/ARCA (facturas, notas de crédito y notas de débito) con CAE, y leer o escribir tu catálogo, tus ventas, tus clientes, tus compras, tu contabilidad y más. Es una funcionalidad del **plan Premium** (las cuentas en período de prueba también tienen acceso).

## Obtené tu API token

1. Entrá al panel de YoFacturo → **Configuración → Integraciones → API Tokens → «Crear token»**.
2. Elegí un nombre, una expiración (30/60/90 días, 1 año o sin vencimiento) y los *scopes* (permisos) que va a usar la integración.
3. El token se muestra **una sola vez**. Guardalo como un secreto (variable de entorno, gestor de secretos) — nunca en el código fuente ni en el frontend, y nunca en la URL o en query params.

El token viaja en el header `X-API-Key` (o, si lo preferís, `Authorization: Bearer`) en cada petición. La URL base es `https://api.yo-facturo.com` con el prefijo `/api/v1/`.

```bash
curl https://api.yo-facturo.com/api/v1/products/list/ \
  -H "X-API-Key: TU_TOKEN"
```

## Quickstart

### Instalación

```bash
pip install yofacturo          # Python
npm install yofacturo          # Node.js / TypeScript
composer require yofacturo/yofacturo-php   # PHP
```

### Emitir una factura

<details open>
<summary>Python</summary>

```python
from yofacturo import YoFacturo

client = YoFacturo(api_key="yf_live_...")

factura = client.invoices.create(
    punto_venta=1,  # tu punto de venta habilitado en ARCA
    tipo_documento=99,  # Consumidor Final
    numero_documento="0",
    razon_social="CONSUMIDOR FINAL",
    items=[{"descripcion": "Servicio de consultoría", "cantidad": 1, "precio_unitario": 15000}],
    autorizar=True,  # dispara la autorización ante AFIP en segundo plano
)
print(factura["data"]["id"])
```
</details>

<details>
<summary>Node.js / TypeScript</summary>

```ts
import { YoFacturo } from "yofacturo";

const client = new YoFacturo("yf_live_...");

const factura = await client.invoices.create({
  punto_venta: 1, // tu punto de venta habilitado en ARCA
  tipo_documento: 99, // Consumidor Final
  numero_documento: "0",
  razon_social: "CONSUMIDOR FINAL",
  items: [{ descripcion: "Servicio de consultoría", cantidad: 1, precio_unitario: 15000 }],
  autorizar: true, // dispara la autorización ante AFIP en segundo plano
});
console.log(factura.data.id);
```
</details>

<details>
<summary>PHP</summary>

```php
use YoFacturo\Client;

$client = new Client('yf_live_...');

$factura = $client->invoices->create([
    'punto_venta' => 1, // tu punto de venta habilitado en ARCA
    'tipo_documento' => 99, // Consumidor Final
    'numero_documento' => '0',
    'razon_social' => 'CONSUMIDOR FINAL',
    'items' => [['descripcion' => 'Servicio de consultoría', 'cantidad' => 1, 'precio_unitario' => 15000]],
    'autorizar' => true, // dispara la autorización ante AFIP en segundo plano
]);
echo $factura['data']['id'];
```
</details>

<details>
<summary>cURL</summary>

```bash
curl -X POST https://api.yo-facturo.com/api/v1/bill/receipts/invoice/ \
  -H "X-API-Key: TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "punto_venta": 1,
    "concepto": 1,
    "tipo_documento": 99,
    "numero_documento": "0",
    "razon_social": "CONSUMIDOR FINAL",
    "items": [{"descripcion": "Servicio de consultoría", "cantidad": 1, "precio_unitario": 15000}],
    "autorizar": true
  }'
```
</details>

**Qué manda cada campo.** `punto_venta` es obligatorio (el punto de venta habilitado en ARCA). `concepto` también lo exige la API (1 = productos, 2 = servicios, 3 = ambos): los SDKs mandan `1` si no lo pasás. Los `precio_unitario` son **precios finales, IVA incluido** (igual que el POS y el catálogo): el backend calcula neto, IVA y total, así que no mandes `importe_*` ni `iva_items`. Si tus precios son netos de IVA, mandá `precios_con_iva: false`. La letra (A/B/C) sale de la condición de IVA del receptor, que podés indicar con `condicion_iva_receptor_id` (1 RI, 4 Exento, 5 Consumidor Final, 6 Monotributo) o con `receptor_condicion_iva` / `condicion_iva` (el nombre): los tres campos valen lo mismo. Con un CUIT solo, la API consulta el padrón de ARCA; si no puede determinar la condición, emite Factura B a Consumidor Final. Una línea puede llevar `bonificacion` (descuento) y `iva_id` (5 = 21%, 4 = 10,5%, 3 = 0%).

Con `autorizar: true` el comprobante se crea y la autorización ante AFIP se dispara sola: la respuesta vuelve enseguida con `authorization_pending: true` y el comprobante en estado `pendiente`. Para obtener el **CAE**, volvé a leer el comprobante (`invoices.get(id)`) hasta que el campo `cae` venga cargado. Si preferís revisar el comprobante antes de emitirlo, creálo con `autorizar: false` (queda en borrador) y llamá después a `invoices.authorize(id)`, que es síncrono y devuelve el CAE (o el motivo del rechazo) en el momento.

### Listar comprobantes

```python
comprobantes = client.invoices.list(page=1, per_page=20, estado="aprobado")
```

### Emitir una factura a un cliente registrado

```python
factura = client.invoices.create_for_customer(
    customer_id,  # el "id" del cliente en YoFacturo: documento y condición de IVA salen de su ficha
    punto_venta=1,
    items=[{"descripcion": "Servicio de consultoría", "cantidad": 1, "precio_unitario": 15000}],
)
```

### Emitir una nota de crédito

```python
nota = client.invoices.credit_note(
    comprobante_id,  # el "id" del comprobante original, que debe estar aprobado
    lineas=[{"linea": 0, "cantidad": 1}],  # 1 unidad del primer renglón del original
    motivo="Devolución parcial de mercadería",
)

Cuánto acreditar se indica con **uno** de estos campos: `lineas=[{"linea": 0, "cantidad": 1}]` (devolución por renglón: `linea` es el índice desde 0 del renglón del original), `importe_a_acreditar=605` (un monto) o `porcentaje_aplicar=50` (un porcentaje). Sin ninguno, la nota anula el 100% del comprobante. `items` ya no se usa para devoluciones parciales: la API arma las líneas de la nota desde el original y rechaza (400) un `items` que no coincida con su total.
```

Los ejemplos completos y ejecutables (Python, Node.js y PHP) están en [`examples/`](examples/): [`emitir-factura`](examples/emitir-factura.py), [`listar-comprobantes`](examples/listar-comprobantes.py) y [`nota-de-credito`](examples/nota-de-credito.py).

## Recursos cubiertos

- **`invoices`** — comprobantes electrónicos AFIP/ARCA (`/bill/receipts`): emitir factura, emitir a un cliente registrado, nota de crédito, nota de débito, listar, obtener, autorizar (obtener CAE), anular y tipos de comprobante soportados.
- **`customers`** — clientes (`/customers`): listar, obtener, crear, actualizar, eliminar.
- **`products`** — productos (`/products`): listar, obtener, crear, actualizar, eliminar.
- **`sales`** — ventas (`/sales`): listar, obtener, crear, actualizar, eliminar.
- **`services`** — servicios (`/services`, scope `services:read|write`): listar, obtener, crear, actualizar, eliminar. `list` manda `currency_aware=1` por defecto, igual que `products`.
- **`rentals`** — alquileres (`/rentals`, scope `rentals:read|write`): mismos métodos y mismo `currency_aware` que `products`.
- **`appointments`** (`subscription_plans` en Python, `subscriptionPlans` en Node/PHP) — turnos (`/appointments`, scope `appointments:read|write`) y planes de suscripción (`/subscription-plans`, scope `recurring:read|write`): listar, obtener, crear, actualizar, eliminar. Turnos requiere el módulo de turnos habilitado en el plan.
- **`sifen`** — facturación electrónica de Paraguay (`/bill/sifen`, SIFEN/DNIT): documentos por CDC (listar, obtener, consultar a la SET, eventos, anular, nota de débito, inutilización), KuDE, envío por email y enlace público, nota de crédito por venta, readiness, ambiente, consulta de RUC, numeración, certificados y catálogos; factura sin venta (`create`), sonda de conectividad (`diagnose`), `verify_caja`, consulta de lotes (`lote`) y tipos de documento (`types`, `validate_type`). Nombres: Python `client.sifen.debit_note(...)`, Node/PHP `client.sifen.debitNote(...)`. Guía: [Facturación Paraguay (SIFEN)](https://yo-facturo.com/dev/paraguay-sifen/).
- **`partner`** — cuentas API partner (`/partner`, solo con contrato partner y scopes `taxpayers:*`): registrar el CUIT de tus usuarios finales (`create_taxpayer`), listar con cursor, obtener, dar de baja, verificar la delegación WSFE (`verify_delegation`) y ver el uso del período (`usage`). Después se factura con `client.invoices.create(taxpayer_id=..., ...)`. Nombres: Python `client.partner.create_taxpayer(...)`, Node/PHP `client.partner.createTaxpayer(...)`.

La spec OpenAPI completa (159 rutas, 236 operaciones — catálogo, ventas, facturación, compras, clientes, operaciones, contabilidad, webhooks y sandbox) está en [`openapi/openapi.json`](openapi/openapi.json) / [`openapi/openapi.yaml`](openapi/openapi.yaml), y también se sirve pública en [`https://api.yo-facturo.com/api/v1/openapi.json`](https://api.yo-facturo.com/api/v1/openapi.json). La [colección de Postman](postman/yofacturo.postman_collection.json) cubre las 236 operaciones, agrupadas en carpetas por área, con `{{baseUrl}}` y `{{apiKey}}` como variables.

## Manejo de errores

La API responde con códigos HTTP estándar. Los tres SDKs traducen la respuesta a excepciones tipadas:

| HTTP | Código (`code`) | Excepción |
|---|---|---|
| 401 | `UNAUTHORIZED` | `AuthenticationError` |
| 403 | `FORBIDDEN` | `ScopeError` (alias `PermissionError`) |
| 404 | `NOT_FOUND` | `NotFoundError` |
| 400 / 422 | `VALIDATION_ERROR` / `UNPROCESSABLE_ENTITY` | `ValidationError` (con el detalle por campo) |
| 409 | `CONFLICT` | `ConflictError` |
| 429 | `RATE_LIMITED` | `RateLimitError` (con `retry_after` si la API lo informa) |
| 5xx | `INTERNAL_ERROR` / `SERVICE_UNAVAILABLE` | `ServerError` |

Cualquier otro caso cae en `ApiError`, la excepción base de todos los errores de la API. Los tres clientes reintentan automáticamente (backoff exponencial, hasta 3 veces por defecto) ante `429` y `5xx` — configurable al crear el cliente.

## Límites de uso (rate limits)

Los límites se aplican **por cuenta** y son compartidos entre todos los API tokens de esa cuenta:

| Ventana | Máximo |
|---|---|
| Por segundo | 10 |
| Por minuto | 100 |
| Por hora | 3.000 |
| Por día | 20.000 |

Al superarlos, la API responde `429 Too Many Requests`. Los SDKs reintentan solos con backoff exponencial; si necesitás un límite más alto para tu integración, escribí a `api@yo-facturo.com`.

## Documentación y soporte

- Documentación completa para desarrolladores: **https://yo-facturo.com/dev/**
- Spec OpenAPI pública: **https://api.yo-facturo.com/api/v1/openapi.json**
- Estado del servicio en tiempo real: **https://status.yo-facturo.com**
- Soporte: `api@yo-facturo.com`

## Estructura del repo

```
yo-facturo_sdk/
  openapi/     spec OpenAPI 3.1 (json + yaml)
  postman/     colección de Postman (236 operaciones)
  python/      SDK de Python (paquete `yofacturo`)
  node/        SDK de Node.js/TypeScript (paquete `yofacturo`)
  php/         SDK de PHP (paquete `yofacturo/yofacturo-php`)
  examples/    ejemplos ejecutables (emitir factura, listar, nota de crédito)
```

Cada SDK tiene su propio README con instrucciones de instalación, uso y tests: [`python/README.md`](python/README.md), [`node/README.md`](node/README.md), [`php/README.md`](php/README.md).

## Licencia

[MIT](LICENSE) © 2026 YoFacturo

## CI

El workflow de GitHub Actions está en `ci/ci.yml.example` (no activo). Para activarlo, copiarlo a `.github/workflows/ci.yml`.
