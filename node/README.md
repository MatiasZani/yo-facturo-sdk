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
const nota = await client.invoices.creditNote(
  factura.data.id,
  [{ descripcion: "Devolución parcial", cantidad: 1, precio_unitario: 5000 }],
  { motivo: "Devolución parcial de mercadería" }
);
```

## Recursos

- `client.invoices` — comprobantes AFIP/ARCA: `create`, `createForCustomer`, `creditNote`, `debitNote`, `list`, `get`, `authorize`, `cancel`, `supportedTypes`.
- `client.customers` — `list`, `get`, `create`, `update`, `delete`.
- `client.products` — `list`, `get`, `create`, `update`, `delete`.
- `client.sales` — `list`, `get`, `create`, `update`, `delete`.

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
