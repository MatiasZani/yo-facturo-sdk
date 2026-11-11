/**
 * SDK oficial de Node.js/TypeScript para la API de YoFacturo.
 *
 * Facturación electrónica ARCA/AFIP para Argentina, catálogo, ventas y
 * clientes, de forma programática. Documentación: https://yo-facturo.com/dev/
 */

export { YoFacturo, DEFAULT_BASE_URL, VERSION, SANDBOX_KEY_PREFIX, ENVIRONMENTS, isSandboxKey } from "./client";
export type { Environment, YoFacturoOptions, Transport, TransportResponse, HttpMethod } from "./client";

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

export * as webhooks from "./webhooks";
export { CrudResource } from "./resources/base";
export type { ListParams } from "./resources/base";
export { InvoicesResource } from "./resources/invoices";
export type { InvoiceItem, InvoiceListParams } from "./resources/invoices";
export { CustomersResource } from "./resources/customers";
export { ProductsResource } from "./resources/products";
export { SalesResource } from "./resources/sales";
export { ServicesResource } from "./resources/services";
export type { ServiceListParams } from "./resources/services";
export { RentalsResource } from "./resources/rentals";
export type { RentalListParams } from "./resources/rentals";
export { AppointmentsResource } from "./resources/appointments";
export { SubscriptionPlansResource } from "./resources/subscription-plans";
export { SifenResource } from "./resources/sifen";
export { PartnerResource } from "./resources/partner";
export type { PartnerTaxpayerParams, PartnerListParams } from "./resources/partner";
export type {
  SifenListParams,
  SifenDebitNoteItem,
  SifenNumberingParams,
  SifenCreditNoteLine,
  SifenCreateItem,
  SifenCreateDocument,
  SifenVerifyCaja,
} from "./resources/sifen";
