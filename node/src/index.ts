/**
 * SDK oficial de Node.js/TypeScript para la API de YoFacturo.
 *
 * Facturación electrónica ARCA/AFIP para Argentina, catálogo, ventas y
 * clientes, de forma programática. Documentación: https://yo-facturo.com/dev/
 */

export { YoFacturo, DEFAULT_BASE_URL, VERSION } from "./client";
export type { YoFacturoOptions, Transport, TransportResponse, HttpMethod } from "./client";

export {
  YoFacturoError,
  ApiError,
  AuthenticationError,
  ScopeError,
  PermissionError,
  NotFoundError,
  ValidationError,
  ConflictError,
  RateLimitError,
  ServerError,
  errorFromResponse,
} from "./errors";
export type { ApiErrorOptions, RateLimitErrorOptions } from "./errors";

export { CrudResource } from "./resources/base";
export type { ListParams } from "./resources/base";
export { InvoicesResource } from "./resources/invoices";
export type { InvoiceItem, InvoiceListParams } from "./resources/invoices";
export { CustomersResource } from "./resources/customers";
export { ProductsResource } from "./resources/products";
export { SalesResource } from "./resources/sales";
