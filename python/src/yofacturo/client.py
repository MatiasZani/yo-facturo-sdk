"""Cliente HTTP del SDK de YoFacturo.

Sin dependencias externas: usa `urllib` de la librería estándar. El
transporte real es inyectable (parámetro `transport`) para poder testear el
cliente sin red -- ver `python/tests/`.
"""

from __future__ import annotations

import json as _json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from ._version import __version__
from .errors import YoFacturoError, error_from_response
from .resources.customers import CustomersResource
from .resources.invoices import InvoicesResource
from .resources.products import ProductsResource
from .resources.sales import SalesResource

DEFAULT_BASE_URL = "https://api.yo-facturo.com/api/v1"

# (method, url, headers, body, timeout) -> (status_code, headers, raw_body)
Transport = Callable[[str, str, Mapping[str, str], Optional[bytes], float], Tuple[int, Mapping[str, str], bytes]]


def _default_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: Optional[bytes],
    timeout: float,
) -> Tuple[int, Mapping[str, str], bytes]:
    request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        return exc.code, dict(exc.headers.items()) if exc.headers else {}, raw
    except urllib.error.URLError as exc:
        raise YoFacturoError(f"No se pudo conectar con la API de YoFacturo: {exc.reason}") from exc


def _parse_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return _json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {"success": False, "error": raw.decode("utf-8", errors="replace"), "code": None}


def _extract_error(data: Any) -> Tuple[str, Optional[str], Optional[list]]:
    if isinstance(data, dict):
        message = data.get("error") or data.get("message") or "Error desconocido de la API de YoFacturo"
        return message, data.get("code"), data.get("errors")
    return "Error desconocido de la API de YoFacturo", None, None


def _parse_retry_after(headers: Mapping[str, str]) -> Optional[float]:
    for key, value in headers.items():
        if key.lower() == "retry-after":
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


class YoFacturo:
    """Cliente principal del SDK.

    Ejemplo::

        from yofacturo import YoFacturo

        client = YoFacturo(api_key="yf_live_...")
        factura = client.invoices.create(
            tipo_documento=99,
            numero_documento="0",
            razon_social="CONSUMIDOR FINAL",
            items=[{"descripcion": "Servicio", "cantidad": 1, "precio_unitario": 1000}],
            autorizar=True,
        )

    Args:
        api_key: token `yf_live_...` (o `yf_test_...` para sandbox), generado
            desde Configuración → Integraciones → API Tokens en el panel.
        base_url: URL base de la API. Por defecto la de producción.
        timeout: timeout por request, en segundos.
        max_retries: cantidad máxima de reintentos automáticos ante 429 o 5xx
            (con backoff exponencial). 0 desactiva los reintentos.
        transport: función de transporte HTTP; se usa la real (`urllib`) por
            defecto. Pensado para inyectar un doble de prueba en tests.
        sleep: función usada para esperar entre reintentos (por defecto
            `time.sleep`); inyectable para que los tests no esperen de verdad.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30,
        max_retries: int = 3,
        transport: Optional[Transport] = None,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key es obligatorio")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._transport: Transport = transport or _default_transport
        self._sleep: Callable[[float], None] = sleep or time.sleep

        self.invoices = InvoicesResource(self)
        self.customers = CustomersResource(self)
        self.products = ProductsResource(self)
        self.sales = SalesResource(self)

    # -- verbos HTTP -----------------------------------------------------

    def get(self, path: str, *, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json_body: Optional[Mapping[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """POST genérico.

        `idempotency_key` es opcional: si se manda, viaja en el header
        `Idempotency-Key`. La API lo soporta hoy en `POST /sales/`,
        `POST /products/` y `POST /bill/receipts/invoice/` -- reenviar la
        misma clave dentro de las 24h reproduce la respuesta original en vez
        de crear un recurso duplicado.
        """
        extra_headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self.request("POST", path, json_body=json_body, extra_headers=extra_headers)

    def put(self, path: str, *, json_body: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request("PUT", path, json_body=json_body)

    def patch(self, path: str, *, json_body: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request("PATCH", path, json_body=json_body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    # -- request genérico --------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        url = self._build_url(path, params)
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": f"yofacturo-sdk-python/{__version__}",
        }
        if extra_headers:
            headers.update(extra_headers)
        body_bytes: Optional[bytes] = None
        if json_body is not None:
            body_bytes = _json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        attempts = self.max_retries + 1
        for attempt in range(attempts):
            status, resp_headers, raw = self._transport(method, url, headers, body_bytes, self.timeout)
            data = _parse_json(raw)
            if 200 <= status < 300:
                return data

            retry_after = _parse_retry_after(resp_headers)
            retryable = status == 429 or status >= 500
            if retryable and attempt < attempts - 1:
                self._sleep(_backoff_delay(attempt, retry_after))
                continue

            message, code, field_errors = _extract_error(data)
            raise error_from_response(status, code, message, field_errors, data, retry_after=retry_after)

        raise YoFacturoError("No se pudo completar la petición a la API de YoFacturo")  # pragma: no cover

    def _build_url(self, path: str, params: Optional[Mapping[str, Any]]) -> str:
        url = self.base_url + path
        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                url += "?" + urllib.parse.urlencode(filtered)
        return url


def _backoff_delay(attempt: int, retry_after: Optional[float]) -> float:
    if retry_after is not None and retry_after >= 0:
        return retry_after
    base = min(8.0, 0.5 * (2 ** attempt))
    return base + random.uniform(0, 0.25)
