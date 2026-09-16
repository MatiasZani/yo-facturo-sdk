"""Fixtures compartidas. Los tests no tocan la red: inyectan un `transport`
falso en el cliente (ver `yofacturo.client.Transport`) que devuelve
respuestas armadas a mano desde una cola.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import pytest

from yofacturo import YoFacturo

Response = Tuple[int, Dict[str, str], Any]


class FakeTransport:
    def __init__(self, responses: List[Response]) -> None:
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def __call__(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> Tuple[int, Dict[str, str], bytes]:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": json.loads(body.decode("utf-8")) if body else None,
                "timeout": timeout,
            }
        )
        if not self._responses:
            raise AssertionError("FakeTransport se quedó sin respuestas encoladas")
        status, headers_out, payload = self._responses.pop(0)
        if payload is None:
            raw = b""
        elif isinstance(payload, (bytes, bytearray)):
            raw = bytes(payload)
        else:
            raw = json.dumps(payload).encode("utf-8")
        return status, headers_out, raw

    @property
    def last_call(self) -> Dict[str, Any]:
        return self.calls[-1]


@pytest.fixture
def make_client():
    """Fábrica: `make_client([(200, {}, {"success": True, "data": {}})])`."""

    def _make(responses: List[Response], **client_kwargs: Any):
        transport = FakeTransport(responses)
        client = YoFacturo(
            api_key="yf_live_test_token",
            transport=transport,
            sleep=lambda seconds: None,  # tests no esperan de verdad
            **client_kwargs,
        )
        return client, transport

    return _make
