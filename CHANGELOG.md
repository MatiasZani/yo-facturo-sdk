# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

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
