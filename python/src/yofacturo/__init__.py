"""SDK oficial de Python para la API de YoFacturo.

Facturación electrónica ARCA/AFIP para Argentina, catálogo, ventas y
clientes, de forma programática. Documentación: https://yo-facturo.com/dev/
"""

from ._version import __version__
from .client import DEFAULT_BASE_URL, YoFacturo
from .errors import (
    ApiError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ScopeError,
    ServerError,
    ValidationError,
    YoFacturoError,
)

__all__ = [
    "YoFacturo",
    "DEFAULT_BASE_URL",
    "YoFacturoError",
    "ApiError",
    "AuthenticationError",
    "ScopeError",
    "PermissionError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "RateLimitError",
    "ServerError",
    "__version__",
]
