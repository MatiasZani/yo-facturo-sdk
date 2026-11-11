"""Verificación de firmas de webhooks de YoFacturo.

Algoritmo (idéntico al firmador saliente de la API,
`app/internal/managers/webhooks/outbound/webhook_signing.py`)::

    X-YF-Signature: t=<unix_ts>,v1=<hex>
    hex = HMAC_SHA256(secret, "<t>." + <body crudo>)

Hay que firmar sobre los BYTES CRUDOS recibidos, no sobre el JSON
re-serializado. Sin dependencias externas.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Tuple, Union

#: Header HTTP que trae la firma.
SIGNATURE_HEADER = "X-YF-Signature"
#: Tolerancia anti-replay por defecto (segundos), la que documenta la API.
DEFAULT_TOLERANCE_SECONDS = 300

Payload = Union[bytes, bytearray, str]


def _to_bytes(payload: Payload) -> bytes:
    return payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)


def parse_signature_header(header: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    """`"t=<ts>,v1=<hex>"` -> `(timestamp, hex)`; `(None, None)` si está mal formado."""
    if not header:
        return None, None
    timestamp: Optional[int] = None
    signature: Optional[str] = None
    for part in header.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                return None, None
        elif key == "v1":
            signature = value
    return timestamp, signature


def compute_signature(secret: str, timestamp: int, payload: Payload) -> str:
    """Hex HMAC-SHA256 de `"<timestamp>." + payload` con `secret`."""
    signed = f"{timestamp}.".encode("utf-8") + _to_bytes(payload)
    return hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()


def build_signature_header(secret: str, timestamp: int, payload: Payload) -> str:
    """Arma el valor del header (`t=...,v1=...`). Útil para tests propios."""
    return f"t={timestamp},v1={compute_signature(secret, timestamp, payload)}"


def verify_signature(
    secret: str,
    payload: Payload,
    signature_header: Optional[str],
    *,
    tolerance_seconds: Optional[int] = DEFAULT_TOLERANCE_SECONDS,
    now: Optional[float] = None,
) -> bool:
    """True si la firma es válida. Nunca levanta por una firma inválida.

    Args:
        secret: el secret del endpoint (se muestra una sola vez al crearlo).
        payload: body CRUDO tal cual llegó (bytes o str).
        signature_header: valor del header `X-YF-Signature`.
        tolerance_seconds: diferencia máxima con la hora actual (anti-replay,
            300 s por defecto). `None` desactiva el chequeo de timestamp.
        now: hora actual inyectable (tests).
    """
    timestamp, signature = parse_signature_header(signature_header)
    if timestamp is None or not signature or not secret:
        return False
    if tolerance_seconds is not None:
        current = time.time() if now is None else now
        if abs(current - timestamp) > tolerance_seconds:
            return False
    expected = compute_signature(secret, timestamp, payload)
    return hmac.compare_digest(expected, signature)


def construct_event(
    secret: str,
    payload: Payload,
    signature_header: Optional[str],
    *,
    tolerance_seconds: Optional[int] = DEFAULT_TOLERANCE_SECONDS,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Verifica la firma y devuelve el evento (`dict`); `ValueError` si no es válida."""
    if not verify_signature(
        secret, payload, signature_header, tolerance_seconds=tolerance_seconds, now=now
    ):
        raise ValueError("Firma de webhook inválida")
    event = json.loads(_to_bytes(payload).decode("utf-8"))
    if not isinstance(event, dict):
        raise ValueError("El body del webhook no es un objeto JSON")
    return event
