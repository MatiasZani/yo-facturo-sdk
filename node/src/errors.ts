/**
 * Excepciones tipadas del SDK de YoFacturo.
 *
 * Los errores devueltos por la API (HTTP 4xx/5xx) son instancias de
 * `ApiError` y exponen `statusCode`, `code` (identificador estable de la
 * API, ej. "VALIDATION_ERROR") y `errors` (detalle por campo, solo en
 * errores de validación). Ver https://yo-facturo.com/dev/errors/
 */

export class YoFacturoError extends Error {
  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

export interface ApiErrorOptions {
  statusCode?: number;
  code?: string;
  errors?: unknown[];
  responseBody?: unknown;
}

export class ApiError extends YoFacturoError {
  readonly statusCode?: number;
  readonly code?: string;
  readonly errors: unknown[];
  readonly responseBody?: unknown;

  constructor(message: string, options: ApiErrorOptions = {}) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = options.statusCode;
    this.code = options.code;
    this.errors = options.errors ?? [];
    this.responseBody = options.responseBody;
  }
}

/** 401 Unauthorized: falta el token, es inválido, fue revocado o expiró. */
export class AuthenticationError extends ApiError {}

/** 403 Forbidden: el plan no incluye la API, venció la suscripción o falta un scope. */
export class ScopeError extends ApiError {}

/** Alias de `ScopeError`, para paridad con otros SDKs. */
export class PermissionError extends ScopeError {}

/** 404 Not Found: el recurso solicitado no existe. */
export class NotFoundError extends ApiError {}

/** 400/422: la petición está mal formada o no pasa las validaciones de negocio. */
export class ValidationError extends ApiError {}

/** 409 Conflict: la petición choca con el estado actual del recurso. */
export class ConflictError extends ApiError {}

/** 5xx: error interno del servidor o servicio no disponible temporalmente. */
export class ServerError extends ApiError {}

export interface RateLimitErrorOptions extends ApiErrorOptions {
  /**
   * Segundos a esperar antes de reintentar, si la API mandó el header
   * `Retry-After`. Hoy no siempre está presente en producción -- puede ser
   * `undefined`; el cliente igual reintenta con backoff exponencial propio.
   */
  retryAfter?: number;
}

/** 429 Too Many Requests: se superó el límite de frecuencia de la cuenta. */
export class RateLimitError extends ApiError {
  readonly retryAfter?: number;

  constructor(message: string, options: RateLimitErrorOptions = {}) {
    super(message, options);
    this.name = this.constructor.name;
    this.retryAfter = options.retryAfter;
  }
}

export function errorFromResponse(
  statusCode: number,
  code: string | undefined,
  message: string,
  errors: unknown[] | undefined,
  responseBody: unknown,
  retryAfter?: number
): ApiError {
  const options: ApiErrorOptions = { statusCode, code, errors, responseBody };
  switch (statusCode) {
    case 401:
      return new AuthenticationError(message, options);
    case 403:
      return new ScopeError(message, options);
    case 404:
      return new NotFoundError(message, options);
    case 409:
      return new ConflictError(message, options);
    case 400:
    case 422:
      return new ValidationError(message, options);
    case 429:
      return new RateLimitError(message, { ...options, retryAfter });
    default:
      if (statusCode >= 500) return new ServerError(message, options);
      return new ApiError(message, options);
  }
}
