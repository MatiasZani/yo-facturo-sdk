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

from . import webhooks
from .client import ENVIRONMENTS, SANDBOX_KEY_PREFIX, is_sandbox_key

__all__ = [
    "webhooks",
    "is_sandbox_key",
    "SANDBOX_KEY_PREFIX",
    "ENVIRONMENTS",
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
