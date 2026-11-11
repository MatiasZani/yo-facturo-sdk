# yofacturo (Node.js / TypeScript)

SDK oficial de Node.js/TypeScript para la [API de YoFacturo](https://yo-facturo.com/dev/) — facturación electrónica ARCA/AFIP para Argentina, catálogo, ventas y clientes, de forma programática.

Sin dependencias externas (usa el `fetch` global de Node.js >=18). Tipado con TypeScript, se compila a CommonJS + `.d.ts`.

## Instalación

```bash
npm install yofacturo
```

## Uso

```ts
import { YoFacturo } from "yofacturo";

const client = new YoFacturo("yf_live_..."); // Configuración → Integraciones → API Tokens

// Emitir una factura (autorizar: true dispara el CAE en segundo plano)
const factura = await client.invoices.create({
  punto_venta: 1,
  tipo_documento: 99,
  numero_documento: "0",
  razon_social: "CONSUMIDOR FINAL",
  items: [{ descripcion: "Servicio de consultoría", cantidad: 1, precio_unitario: 15000 }],
  autorizar: true,
});
console.log(factura.data.id);

// Listar comprobantes
const comprobantes = await client.invoices.list({ page: 1, per_page: 20, estado: "aprobado" });

// Emitir una nota de crédito asociada
const nota = await client.invoices.creditNote(factura.data.id, {
  lineas: [{ linea: 0, cantidad: 1 }], // 1 unidad del primer renglón (o importe_a_acreditar / porcentaje_aplicar)
  motivo: "Devolución parcial de mercadería",
});
```

## Agent quickstart (English)

```ts
import { YoFacturo, isSandboxKey, webhooks } from "yofacturo";

const client = new YoFacturo(process.env.YOFACTURO_API_KEY!, { environment: "testing" }); // adds "ambiente": "testing"
client.isSandbox; // true for yf_test_ keys (sandbox, synthetic CAE)

const invoice = await client.invoices.create(payload, "order-1234"); // 2nd arg = Idempotency-Key: safe retries
const link = await client.invoices.link(invoice.data.id);            // signed public URL (PDF/HTML)

// In your webhook endpoint, verify the RAW body (not re-serialized JSON):
const event = webhooks.constructEvent(secret, rawBody, req.headers["x-yf-signature"] as string); // throws if invalid
```

Signature scheme: `X-YF-Signature: t=<unix_ts>,v1=<hex>`, `hex = HMAC_SHA256(secret, "<t>." + raw_body)`,
constant-time comparison, 300 s replay tolerance (`toleranceSeconds`). There is no Node CLI: use the Python
`yofacturo` command if you need one.

## Resumen en español

`environment: "testing"` agrega `"ambiente": "testing"` a cada body (homologación ARCA con un token live; los tokens
`yf_test_` son sandbox y no lo necesitan). El segundo argumento de `invoices.create` es el `Idempotency-Key`.
`webhooks.verifySignature` / `constructEvent` validan la firma `X-YF-Signature` sobre el body crudo.

## Recursos

- `client.invoices` — comprobantes AFIP/ARCA: `create`, `createForCustomer`, `creditNote`, `debitNote`, `list`, `get`, `authorize`, `cancel`, `supportedTypes`.
- `client.customers` — `list`, `get`, `create`, `update`, `delete`.
- `client.products` — `list`, `get`, `create`, `update`, `delete`. `list` envía `currency_aware=1` por defecto (productos con `price_currency` en otra moneda, ej. USD; `currency_aware: false` lo desactiva); al vender esos productos mandá `currency` en `sales.create`.
- `client.sales` — `list`, `get`, `create`, `update`, `delete`.
- `client.services`, `client.rentals` — `list`, `get`, `create`, `update`, `delete` (scopes `services:*` / `rentals:*`). `list` envía `currency_aware=1` por defecto, igual que `products` (`currency_aware: false` lo desactiva).
- `client.appointments`, `client.subscriptionPlans` — `list`, `get`, `create`, `update`, `delete` (scopes `appointments:*` / `recurring:*`).

## Manejo de errores

```ts
import { AuthenticationError, ScopeError, NotFoundError, ValidationError, RateLimitError } from "yofacturo";

try {
  await client.invoices.authorize(comprobanteId);
} catch (err) {
  if (err instanceof ValidationError) {
    console.log(err.code, err.errors);
  } else if (err instanceof RateLimitError) {
    console.log("esperar", err.retryAfter, "segundos");
  }
}
```

El cliente reintenta automáticamente (backoff exponencial, hasta 3 veces por defecto) ante `429` y `5xx`. Configurable con `new YoFacturo(apiKey, { maxRetries: ... })`.

## Build y tests

```bash
npm install
npm run build
npm test
```

Los tests (`node:test`) no usan red real: la mayoría inyecta un `transport` falso, y dos casos mockean el `fetch` global para ejercitar el transporte por defecto.

## Links

- Documentación: https://yo-facturo.com/dev/
- Spec OpenAPI: https://api.yo-facturo.com/api/v1/openapi.json
- Estado del servicio: https://status.yo-facturo.com
