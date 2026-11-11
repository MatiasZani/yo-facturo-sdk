# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado

- **Servicios, alquileres, turnos y planes de suscripción:** recursos `services`, `rentals`, `appointments` y `subscription_plans` / `subscriptionPlans` en los tres SDKs (Python, Node.js, PHP), con el mismo CRUD que `products` (`list`, `get`, `create`, `update`, `delete`). `services.list` y `rentals.list` mandan `currency_aware=1` por defecto (igual que `products.list`). Scopes: `services:*`, `rentals:*`, `appointments:*` y `recurring:*`.

- **Productos y ventas en moneda extranjera (USD):** un producto puede tener `price_currency` (ej. `"USD"`; omitido = moneda por defecto de la cuenta) y una venta o presupuesto con esos productos debe mandar `currency` con la misma moneda. Sin `currency` la API responde 422 `CURRENCY_REQUIRED`, con monedas mezcladas 422 `MIXED_CURRENCY_CART`, y los demas errores traen `error_code` (`FOREIGN_CURRENCY_NOT_SUPPORTED`, `INVOICE_FX_RATE_*`, `SALE_TENDER_*`). La venta/presupuesto guarda `currency` y `fx` {rate, rate_date, source, monid, environment} (cotizacion oficial ARCA, calculada por el servidor); los cobros en pesos de una venta en dolares llevan `currency`/`tendered_amount`/`rate`. Las ventas en la moneda por defecto no cambian (no traen `currency` ni `fx`). **Importante para integraciones:** `GET /products/list/` (y `by-barcode`) omite ahora los productos en otra moneda salvo que mandes `currency_aware=1`; los tres SDKs (`products.list`) lo envian por defecto (`currency_aware=False` / `currency_aware: false` / `['currency_aware' => false]` para desactivarlo). La spec OpenAPI documenta `price_currency`, `currency`, `fx`, el parametro `currency_aware` y los `error_code`.

- **Paraguay (SIFEN):** recurso `sifen` en los tres SDKs (Python, Node.js, PHP) con los mismos métodos: `list`, `get`, `query`, `events`, `void`, `debit_note[_preview]`, `inutilizar`, `kude`, `sale_kude`, `send_email`, `public_link`, `generate_invoice`, `credit_note[_preview]`, `receptor_event`, `readiness`, `set_environment`, `certificates`, `ruc`, `numbering`, `seed_numbering` y `catalogs`. Además: `create` (factura sin venta, `POST /bill/sifen/documents/`), `diagnose` (sonda de conectividad mTLS), `verify_caja`, `lote` (consulta en vivo de un lote), `types` y `validate_type`; `POST /sales/totals-preview/` devuelve el bloque `sifen` (IVA 10/5/exento, redondeo, total) en cuentas de Paraguay, y una alícuota que SIFEN no admite en una venta con factura responde 400. La spec OpenAPI y la colección de Postman incluyen la carpeta «Facturación Paraguay».

- **Cuentas API partner:** recurso `partner` en los tres SDKs (Python, Node.js, PHP) para las cuentas con contrato partner (`/partner`): `create_taxpayer`, `list_taxpayers`, `get_taxpayer`, `remove_taxpayer`, `verify_delegation` y `usage` (Node/PHP: `createTaxpayer`, etc.). Se factura en nombre de cada CUIT registrado pasando `taxpayer_id` a `invoices.create`. La spec OpenAPI documenta el tag «Cuentas API partner», el campo `taxpayer_id` y los `error_code` `API_PARTNER_*`.

## [0.3.0] - 2026-10-13

### Agregado

- **Webhooks:** `webhooks.verify_signature` / `construct_event` (Python) y `webhooks.verifySignature` / `constructEvent` (Node) validan `X-YF-Signature` (`t=<ts>,v1=HMAC_SHA256(secret, "<ts>.<body crudo>")`, tolerancia 300 s). Eventos `invoice.rejected` / `invoice.cancelled` documentados en la spec.
- **Sandbox y ambiente:** `is_sandbox_key` / `client.is_sandbox` (tokens `yf_test_`) y parametro `environment="testing"` que agrega `"ambiente"` a los bodies.
- **`invoices.link(id)`** (`POST /bill/receipts/{id}/public-link/`) en Python y Node; `idempotency_key` ya soportado en `invoices.create`.
- **CLI `yofacturo` (Python):** `login`, `invoice create|get|link`, `webhooks verify`; salida JSON y exit code distinto de 0 ante fallos. Extra opcional `yofacturo[keyring]`.
- Spec OpenAPI sincronizada con la API (webhooks `test`/`rotate-secret`, `public-link`, `afip-environment`, `credit-note/preview`).

### Cambiado

- URLs de `Source`/`Homepage` corregidas (`github.com/MatiasZani/yo-facturo-sdk`, `yo-facturo.com/dev/`).

## [0.2.0] - 2026-10-05

La facturación por API ahora usa la misma lógica que el POS y que el panel:
precios finales, una sola regla de letra y de condición del receptor.

### Cambios que pueden afectar tu integración

- **Los precios de `invoices.create` son finales (IVA incluido) por defecto.**
  `POST /bill/receipts/invoice/` y `POST /bill/receipts/invoice/customer/`
  leen `precio_unitario` como precio final, igual que el POS y el catálogo:
  una línea de 1.210 con IVA 21% se emite como neto 1.000 + IVA 210 = 1.210.
  Hasta ahora se leía como neto y el IVA se sumaba encima (la misma línea
  salía en 1.464,10). **Si tu integración manda precios netos de IVA, agregá
  `precios_con_iva: false` al body** (en Python `precios_con_iva=False`, en
  Node `precios_con_iva: false`, en PHP `'precios_con_iva' => false`) y todo
  sigue como antes. Si ya mandabas precios finales, no tenés que hacer nada:
  el total ahora coincide con lo que mandás.
- **`invoices.create_for_customer` / `createForCustomer` ahora factura al
  cliente.** Antes publicaba en `/invoice/`, descartaba el `customer_id` y
  emitía a un Consumidor Final anónimo. Ahora usa
  `POST /bill/receipts/invoice/customer/` y toma documento, razón social y
  condición de IVA de la ficha del cliente. Requiere `punto_venta` en los
  campos, y la respuesta trae el id del comprobante en `data.factura_id` (no en
  `data.id`).
- **`invoices.credit_note`**: `items` pasó a ser opcional. La API arma las
  líneas de la nota desde el comprobante original; un `items` que no
  coincida con el total de la nota se rechaza con 400 (lo mismo que pasaba
  antes con el ejemplo documentado). Para devoluciones parciales usá
  `lineas`, `importe_a_acreditar` o `porcentaje_aplicar` (ver abajo). Las
  llamadas existentes con `items` + `importe_total` siguen funcionando igual.

### Corregido

- **Devolución parcial por renglón** (nota de crédito): se agregan `lineas`
  (`[{"linea": 0, "cantidad": 1}]`, `linea` = índice desde 0 del renglón del
  original), `importe_a_acreditar` y `porcentaje_aplicar`. Sin ninguno, la nota
  anula el 100%. El ejemplo anterior (`items` + `motivo`) siempre devolvía 400.
- **Body mínimo de `invoices.create`**: la API exige `punto_venta` y `concepto`
  y ninguno estaba documentado, así que el ejemplo del README devolvía 400. Ahora
  el SDK manda `concepto = 1` (productos) si no lo indicás, y `punto_venta` figura
  como obligatorio en la documentación, los ejemplos y la spec.
- **`bonificacion` (descuento de línea) en facturas A y B**: se aceptaba solo en
  facturas C; en A/B daba 400. Ya funciona en todas.
- **Condición de IVA del receptor**: `condicion_iva_receptor_id`,
  `receptor_condicion_iva` y `condicion_iva` valen lo mismo y definen tanto la letra
  como el dato que se informa a ARCA. Antes cada campo alimentaba una parte distinta
  y, por ejemplo, un receptor Exento declarado con `receptor_condicion_iva` salía como
  Factura B con condición Consumidor Final.
- **CUIT sin condición**: la API consulta el padrón de ARCA (como el POS), así que un
  Responsable Inscripto recibe Factura A. Si el padrón no puede determinar la
  condición, se emite Factura B a Consumidor Final.
- **`/bill/receipts/invoice/customer/`** ya no exige un domicilio fiscal en la ficha
  del cliente (ARCA no lo pide).

### Documentación

- Guía `/dev/invoices/`, spec OpenAPI, colección de Postman, READMEs y ejemplos
  actualizados: precios finales, campos obligatorios, condición del receptor,
  `iva_id`/`bonificacion` por línea, nota de crédito por renglón/monto/porcentaje y
  nota de débito (precios netos + `importe_total`). Los ejemplos de la guía se
  validan contra la API en cada release (`contract/documented_examples.json`).
- Los ejemplos con CUIT inválido (dígito verificador) se reemplazaron por uno válido.

### En preparación (todavía no vigente)

- `Idempotency-Key` en `POST /pos/<pv>/sale/`, en la creación masiva de ventas y en
  notas de crédito y de débito; deduplicación de facturas solo por clave explícita
  (hoy, sin la clave, dos facturas idénticas en 5 minutos se unifican en una);
  `POST /sales/` con `generate_invoice` en cola ante una caída de ARCA. Se anunciará
  en este changelog cuando estén en producción.

## [0.1.0] - 2026-09-16

### Agregado

- Primera versión pública de los SDKs oficiales de YoFacturo: Python
  (`yofacturo`), Node.js/TypeScript (`yofacturo`) y PHP
  (`yofacturo/yofacturo-php`).
- Recursos: `invoices` (facturación electrónica AFIP/ARCA -- emitir,
  emitir a un cliente registrado, nota de crédito, nota de débito, listar,
  obtener, autorizar, anular, tipos soportados), `customers`, `products` y
  `sales` (CRUD estándar: listar, obtener, crear, actualizar, eliminar).
- Errores tipados por código HTTP: `AuthenticationError` (401),
  `ScopeError`/`PermissionError` (403), `NotFoundError` (404),
  `ValidationError` (400/422), `ConflictError` (409), `RateLimitError`
  (429, con `retry_after` cuando la API lo informa) y `ServerError`/
  `ApiError` como catch-all.
- Reintento automático con backoff exponencial ante `429` y `5xx` (máximo 3
  reintentos por defecto, configurable).
- Soporte opcional para el header `Idempotency-Key` en las creaciones que
  la API soporta hoy (`invoices.create`, `products.create`, `sales.create`).
- Spec OpenAPI 3.1 (`openapi/openapi.json` y `.yaml`) y colección de
  Postman (`postman/yofacturo.postman_collection.json`) generada a partir
  de la spec, con las 189 operaciones agrupadas por área.
- Ejemplos ejecutables en `examples/` (emitir factura, listar comprobantes,
  emitir nota de crédito) en Python, Node.js y PHP.
