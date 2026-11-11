/**
 * Cliente HTTP del SDK de YoFacturo.
 *
 * Sin dependencias externas: usa el `fetch` global de Node.js (>=18). El
 * transporte real es inyectable (opción `transport`) para poder testear el
 * cliente sin red -- ver `node/tests/`.
 */

import { InvoicesResource } from "./resources/invoices";
import { SifenResource } from "./resources/sifen";
import { PartnerResource } from "./resources/partner";
import { CustomersResource } from "./resources/customers";
import { AppointmentsResource } from "./resources/appointments";
import { ProductsResource } from "./resources/products";
import { RentalsResource } from "./resources/rentals";
import { ServicesResource } from "./resources/services";
import { SubscriptionPlansResource } from "./resources/subscription-plans";
import { SalesResource } from "./resources/sales";
import { errorFromResponse, YoFacturoError } from "./errors";

export const DEFAULT_BASE_URL = "https://api.yo-facturo.com/api/v1";
export const VERSION = "0.3.0";
export const SANDBOX_KEY_PREFIX = "yf_test_";
export const ENVIRONMENTS = ["testing", "production"] as const;
export type Environment = (typeof ENVIRONMENTS)[number];

/** true si el token es de sandbox (`yf_test_...`): CAE sintético, sin ARCA real. */
export function isSandboxKey(apiKey?: string | null): boolean {
  return !!apiKey && apiKey.startsWith(SANDBOX_KEY_PREFIX);
}

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface TransportResponse {
  status: number;
  headers: Record<string, string>;
  body: unknown;
}

export type Transport = (
  method: HttpMethod,
  url: string,
  headers: Record<string, string>,
  body: string | undefined,
  timeoutMs: number
) => Promise<TransportResponse>;

export interface YoFacturoOptions {
  /** URL base de la API. Por defecto la de producción. */
  baseUrl?: string;
  /** Timeout por request, en segundos. Default: 30. */
  timeout?: number;
  /** Reintentos automáticos ante 429/5xx, con backoff exponencial. Default: 3. */
  maxRetries?: number;
  /** Transporte HTTP inyectable (para tests). Por defecto usa `fetch`. */
  transport?: Transport;
  /** Función de espera entre reintentos (para tests). Por defecto `setTimeout`. */
  sleep?: (ms: number) => Promise<void>;
  /**
   * `"testing"` o `"production"`. Si se pasa, se agrega `"ambiente"` a cada body JSON
   * que no lo traiga (homologación ARCA con un token live). Con `yf_test_` no hace falta.
   */
  environment?: Environment;
}

interface RequestOptions {
  params?: Record<string, unknown>;
  jsonBody?: Record<string, unknown>;
  extraHeaders?: Record<string, string>;
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function defaultTransport(
  method: HttpMethod,
  url: string,
  headers: Record<string, string>,
  body: string | undefined,
  timeoutMs: number
): Promise<TransportResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { method, headers, body, signal: controller.signal });
    const text = await response.text();
    const responseHeaders: Record<string, string> = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });
    let parsed: unknown = null;
    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = { success: false, error: text, code: null };
      }
    }
    return { status: response.status, headers: responseHeaders, body: parsed };
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new YoFacturoError("Se agotó el timeout esperando a la API de YoFacturo");
    }
    const reason = err instanceof Error ? err.message : String(err);
    throw new YoFacturoError(`No se pudo conectar con la API de YoFacturo: ${reason}`);
  } finally {
    clearTimeout(timer);
  }
}

function parseRetryAfter(headers: Record<string, string>): number | undefined {
  for (const key of Object.keys(headers)) {
    if (key.toLowerCase() === "retry-after") {
      const value = Number(headers[key]);
      return Number.isNaN(value) ? undefined : value;
    }
  }
  return undefined;
}

function extractError(body: unknown): { message: string; code?: string; errors?: unknown[] } {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    const message =
      (typeof b.error === "string" && b.error) ||
      (typeof b.message === "string" && b.message) ||
      "Error desconocido de la API de YoFacturo";
    return {
      message,
      code: typeof b.code === "string" ? b.code : undefined,
      errors: Array.isArray(b.errors) ? b.errors : undefined,
    };
  }
  return { message: "Error desconocido de la API de YoFacturo" };
}

function backoffDelayMs(attempt: number, retryAfter?: number): number {
  if (retryAfter !== undefined && retryAfter >= 0) return retryAfter * 1000;
  const base = Math.min(8000, 500 * 2 ** attempt);
  return base + Math.random() * 250;
}

export class YoFacturo {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly timeout: number;
  readonly maxRetries: number;
  readonly environment?: Environment;
  private readonly transport: Transport;
  private readonly sleep: (ms: number) => Promise<void>;

  readonly invoices: InvoicesResource;
  readonly customers: CustomersResource;
  readonly products: ProductsResource;
  readonly services: ServicesResource;
  readonly rentals: RentalsResource;
  readonly appointments: AppointmentsResource;
  readonly subscriptionPlans: SubscriptionPlansResource;
  readonly sales: SalesResource;
  readonly sifen: SifenResource;
  readonly partner: PartnerResource;

  constructor(apiKey: string, options: YoFacturoOptions = {}) {
    if (!apiKey) {
      throw new Error("apiKey es obligatorio");
    }
    this.apiKey = apiKey;
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.timeout = options.timeout ?? 30;
    this.maxRetries = options.maxRetries ?? 3;
    if (options.environment !== undefined && !ENVIRONMENTS.includes(options.environment)) {
      throw new Error("environment debe ser 'testing' o 'production'");
    }
    this.environment = options.environment;
    this.transport = options.transport ?? defaultTransport;
    this.sleep = options.sleep ?? defaultSleep;

    this.invoices = new InvoicesResource(this);
    this.customers = new CustomersResource(this);
    this.products = new ProductsResource(this);
    this.services = new ServicesResource(this);
    this.rentals = new RentalsResource(this);
    this.appointments = new AppointmentsResource(this);
    this.subscriptionPlans = new SubscriptionPlansResource(this);
    this.sales = new SalesResource(this);
    this.sifen = new SifenResource(this);
    this.partner = new PartnerResource(this);
  }

  /** true si el token es `yf_test_...` (sandbox). */
  get isSandbox(): boolean {
    return isSandboxKey(this.apiKey);
  }

  get<T = any>(path: string, params?: Record<string, unknown>): Promise<T> {
    return this.request<T>("GET", path, { params });
  }

  /**
   * POST genérico. `idempotencyKey` es opcional: si se manda, viaja en el
   * header `Idempotency-Key`. La API lo soporta hoy en `POST /sales/`,
   * `POST /products/` y `POST /bill/receipts/invoice/` -- reenviar la misma
   * clave dentro de las 24h reproduce la respuesta original en vez de crear
   * un recurso duplicado.
   */
  post<T = any>(path: string, jsonBody?: Record<string, unknown>, idempotencyKey?: string): Promise<T> {
    const extraHeaders = idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined;
    return this.request<T>("POST", path, { jsonBody, extraHeaders });
  }

  put<T = any>(path: string, jsonBody?: Record<string, unknown>): Promise<T> {
    return this.request<T>("PUT", path, { jsonBody });
  }

  patch<T = any>(path: string, jsonBody?: Record<string, unknown>): Promise<T> {
    return this.request<T>("PATCH", path, { jsonBody });
  }

  delete<T = any>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }

  async request<T = any>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
    const { params, extraHeaders } = options;
    let jsonBody = options.jsonBody;
    if (jsonBody !== undefined && this.environment && !("ambiente" in jsonBody)) {
      jsonBody = { ...jsonBody, ambiente: this.environment };
    }
    const url = this.buildUrl(path, params);
    const headers: Record<string, string> = {
      "X-API-Key": this.apiKey,
      Accept: "application/json",
      "User-Agent": `yofacturo-sdk-node/${VERSION}`,
      ...extraHeaders,
    };
    let body: string | undefined;
    if (jsonBody !== undefined) {
      body = JSON.stringify(jsonBody);
      headers["Content-Type"] = "application/json";
    }

    const attempts = this.maxRetries + 1;
    for (let attempt = 0; attempt < attempts; attempt++) {
      const response = await this.transport(method, url, headers, body, this.timeout * 1000);
      if (response.status >= 200 && response.status < 300) {
        return response.body as T;
      }

      const retryAfter = parseRetryAfter(response.headers);
      const retryable = response.status === 429 || response.status >= 500;
      if (retryable && attempt < attempts - 1) {
        await this.sleep(backoffDelayMs(attempt, retryAfter));
        continue;
      }

      const { message, code, errors } = extractError(response.body);
      throw errorFromResponse(response.status, code, message, errors, response.body, retryAfter);
    }

    /* istanbul ignore next -- inalcanzable: el loop siempre retorna o lanza */
    throw new YoFacturoError("No se pudo completar la petición a la API de YoFacturo");
  }

  private buildUrl(path: string, params?: Record<string, unknown>): string {
    let url = this.baseUrl + path;
    if (params) {
      const usp = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null) {
          usp.append(key, String(value));
        }
      }
      const qs = usp.toString();
      if (qs) url += `?${qs}`;
    }
    return url;
  }
}
