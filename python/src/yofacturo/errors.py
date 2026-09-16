"""Excepciones tipadas del SDK de YoFacturo.

Todas las excepciones que puede levantar el cliente heredan de
``YoFacturoError``. Los errores devueltos por la API (HTTP 4xx/5xx) heredan
de ``ApiError`` y exponen ``status_code``, ``code`` (el identificador estable
que devuelve la API, ej. ``"VALIDATION_ERROR"``) y ``errors`` (detalle por
campo, solo en errores de validación).

Ver la guía de errores de la API: https://yo-facturo.com/dev/errors/
"""

from __future__ import annotations

from typing import Any, List, Optional


class YoFacturoError(Exception):
    """Excepción base de todas las excepciones del SDK."""


class ApiError(YoFacturoError):
    """Error devuelto por la API que no tiene un tipo más específico.

    Attributes:
        message: mensaje legible (campo ``error`` de la respuesta).
        status_code: código de estado HTTP de la respuesta.
        code: código estable de la API (campo ``code``, ej. ``"NOT_FOUND"``).
        errors: detalle de errores de validación, si la API lo devolvió.
        response_body: cuerpo completo de la respuesta (dict), para debugging.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        errors: Optional[List[Any]] = None,
        response_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.errors = errors or []
        self.response_body = response_body

    def __str__(self) -> str:  # pragma: no cover - repr simple
        parts = [self.message]
        if self.code:
            parts.append(f"(code={self.code})")
        if self.status_code:
            parts.append(f"[HTTP {self.status_code}]")
        return " ".join(parts)


class AuthenticationError(ApiError):
    """401 Unauthorized: falta el token, es inválido, fue revocado o expiró."""


class ScopeError(ApiError):
    """403 Forbidden: el plan no incluye la API, venció la suscripción o falta un scope."""


# Alias por si tu integración prefiere este nombre. Convive con el builtin
# `PermissionError` solo dentro de este módulo: importalo explícitamente,
# `from yofacturo.errors import PermissionError`, o usá `yofacturo.ScopeError`.
PermissionError = ScopeError


class NotFoundError(ApiError):
    """404 Not Found: el recurso solicitado no existe."""


class ValidationError(ApiError):
    """400/422: la petición está mal formada o no pasa las validaciones de negocio.

    Cuando la API devuelve un array ``errors`` con el detalle por campo,
    queda disponible en el atributo homónimo.
    """


class ConflictError(ApiError):
    """409 Conflict: la petición choca con el estado actual del recurso."""


class RateLimitError(ApiError):
    """429 Too Many Requests: se superó el límite de frecuencia de la cuenta.

    ``retry_after`` viene del header ``Retry-After`` cuando la API lo incluye.
    Hoy ese header no siempre está presente en producción, así que puede ser
    ``None`` -- el cliente igual reintenta con backoff exponencial propio
    (ver ``YoFacturo(max_retries=...)``).
    """

    def __init__(self, *args: Any, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ServerError(ApiError):
    """5xx: error interno del servidor o servicio no disponible temporalmente."""


def error_from_response(
    status_code: int,
    code: Optional[str],
    message: str,
    errors: Optional[List[Any]],
    response_body: Any,
    *,
    retry_after: Optional[float] = None,
) -> ApiError:
    """Arma la excepción tipada correcta a partir de una respuesta de error."""

    kwargs = dict(status_code=status_code, code=code, errors=errors, response_body=response_body)
    if status_code == 401:
        return AuthenticationError(message, **kwargs)
    if status_code == 403:
        return ScopeError(message, **kwargs)
    if status_code == 404:
        return NotFoundError(message, **kwargs)
    if status_code == 409:
        return ConflictError(message, **kwargs)
    if status_code in (400, 422):
        return ValidationError(message, **kwargs)
    if status_code == 429:
        return RateLimitError(message, retry_after=retry_after, **kwargs)
    if status_code is not None and status_code >= 500:
        return ServerError(message, **kwargs)
    return ApiError(message, **kwargs)
