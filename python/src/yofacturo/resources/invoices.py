"""Comprobantes electrónicos AFIP/ARCA -- `/bill/receipts`.

Scope requerido: `invoices:read` para leer, `invoices:write` para emitir o
modificar comprobantes. Guía completa: https://yo-facturo.com/dev/invoices/
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ..client import YoFacturo

_BASE = "/bill/receipts"


class InvoicesResource:
    def __init__(self, client: "YoFacturo") -> None:
        self._client = client

    def create(self, *, idempotency_key: Optional[str] = None, **fields: Any) -> Any:
        """Emite un comprobante -- `POST /bill/receipts/invoice/`.

        `tipo_documento`, `numero_documento` e `items` son obligatorios;
        `tipo_comprobante` (A/B/C) se infiere de la condición de IVA del
        emisor si se omite. Con `autorizar=True` la autorización ante AFIP
        se dispara en segundo plano: la respuesta vuelve con
        `authorization_pending: true` y hay que releer el comprobante
        (`get`) hasta que el campo `cae` venga cargado. Con `autorizar=False`
        (default) el comprobante queda en borrador para autorizar después
        con `authorize()`. `idempotency_key` es opcional: evita duplicar el
        comprobante si necesitás reintentar tras un timeout de red.
        """
        return self._client.post(f"{_BASE}/invoice/", json_body=fields, idempotency_key=idempotency_key)

    def create_for_customer(self, customer_id: str, **fields: Any) -> Any:
        """Emite una factura a un cliente ya registrado.

        Usa el mismo endpoint que `create()`, pero resuelve los datos
        fiscales del receptor a partir de `customer_id` en vez de mandarlos
        sueltos (`tipo_documento`, `numero_documento`, `razon_social`, ...).
        """
        return self.create(customer_id=customer_id, **fields)

    def credit_note(
        self,
        comprobante_asociado_id: str,
        items: List[Dict[str, Any]],
        **fields: Any,
    ) -> Any:
        """Emite una nota de crédito -- `POST /bill/receipts/credit-note/`.

        `comprobante_asociado_id` (el `id` del comprobante original, que
        debe estar aprobado) e `items` son obligatorios.
        """
        body: Dict[str, Any] = {
            "comprobante_asociado_id": comprobante_asociado_id,
            "items": items,
            **fields,
        }
        return self._client.post(f"{_BASE}/credit-note/", json_body=body)

    def debit_note(
        self,
        comprobante_asociado_id: str,
        items: List[Dict[str, Any]],
        **fields: Any,
    ) -> Any:
        """Emite una nota de débito -- `POST /bill/receipts/debit-note/`."""
        body: Dict[str, Any] = {
            "comprobante_asociado_id": comprobante_asociado_id,
            "items": items,
            **fields,
        }
        return self._client.post(f"{_BASE}/debit-note/", json_body=body)

    def list(
        self,
        *,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        sort_dir: Optional[int] = None,
        fields: Optional[str] = None,
        tipo_comprobante: Optional[int] = None,
        estado: Optional[str] = None,
        **extra: Any,
    ) -> Any:
        """Lista comprobantes con paginación y filtros -- `GET /bill/receipts/list/`."""
        params: Dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "search": search,
            "sort": sort,
            "sort_dir": sort_dir,
            "fields": fields,
            "tipo_comprobante": tipo_comprobante,
            "estado": estado,
            **extra,
        }
        return self._client.get(f"{_BASE}/list/", params=params)

    def get(self, comprobante_id: str) -> Any:
        """Obtiene un comprobante por su id -- `GET /bill/receipts/{id}/`."""
        return self._client.get(f"{_BASE}/{comprobante_id}/")

    def authorize(self, comprobante_id: str) -> Any:
        """Autoriza un comprobante en borrador ante AFIP (obtiene el CAE).

        `POST /bill/receipts/authorize/{id}/`. A diferencia de `create()`
        con `autorizar=True`, esta llamada es síncrona: espera a AFIP y, si
        lo aprueba, la respuesta ya trae `cae` y `cae_vencimiento`. Si AFIP
        lo rechaza, levanta `ValidationError` con el motivo.
        """
        return self._client.post(f"{_BASE}/authorize/{comprobante_id}/", json_body={})

    def cancel(self, comprobante_id: str, *, motivo: Optional[str] = None) -> Any:
        """Anula un comprobante ya autorizado -- `POST /bill/receipts/cancel/{id}/`.

        Genera automáticamente una nota de crédito por el importe total del
        comprobante original (viene en `data.nota_credito` de la respuesta).
        """
        body: Dict[str, Any] = {}
        if motivo is not None:
            body["motivo"] = motivo
        return self._client.post(f"{_BASE}/cancel/{comprobante_id}/", json_body=body)

    def supported_types(self) -> Any:
        """Tipos de comprobante soportados según la condición fiscal del emisor.

        `GET /bill/receipts/supported-types/`.
        """
        return self._client.get(f"{_BASE}/supported-types/")
