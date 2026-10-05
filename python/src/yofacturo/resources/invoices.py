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

        Obligatorios: `punto_venta`, `tipo_documento`, `numero_documento` e
        `items`. `concepto` (1 = productos, 2 = servicios, 3 = ambos) es
        obligatorio para la API: el SDK manda `concepto=1` si no lo pasás.
        `tipo_comprobante` (A/B/C) se infiere de la condición de IVA del
        emisor y del receptor si se omite.

        Los `precio_unitario` de `items` son precios FINALES (IVA incluido,
        como en el POS) y el backend calcula neto, IVA y total: no hace falta
        mandar `importe_*` ni `iva_items`. Para mandar precios NETOS de IVA
        pasá `precios_con_iva=False`.

        La condición de IVA del receptor se resuelve con la misma regla que el
        POS: pasá `condicion_iva_receptor_id` (código ARCA: 1 RI, 4 Exento,
        5 Consumidor Final, 6 Monotributo) o, equivalentes, `receptor_condicion_iva`
        / `condicion_iva` con el nombre. Con un CUIT solo, la API consulta el
        padrón de ARCA; si no puede determinarla emite Factura B a Consumidor Final.

        Con `autorizar=True` la autorización ante AFIP se dispara en segundo
        plano: la respuesta vuelve con `authorization_pending: true` y hay que
        releer el comprobante (`get`) hasta que el campo `cae` venga cargado.
        Con `autorizar=False` (default) el comprobante queda en borrador para
        autorizar después con `authorize()`. `idempotency_key` es opcional:
        evita duplicar el comprobante si necesitás reintentar tras un timeout
        de red.
        """
        fields.setdefault("concepto", 1)
        return self._client.post(f"{_BASE}/invoice/", json_body=fields, idempotency_key=idempotency_key)

    def create_for_customer(
        self, customer_id: str, *, idempotency_key: Optional[str] = None, **fields: Any
    ) -> Any:
        """Emite una factura a un cliente ya registrado -- `POST /bill/receipts/invoice/customer/`.

        La API toma documento, razón social y condición de IVA de la ficha del
        cliente (`customer_id`), así que no se mandan `tipo_documento`,
        `numero_documento` ni la condición. Obligatorios: `punto_venta` e
        `items` (`concepto` va en 1 si no lo pasás). Los precios, `precios_con_iva`
        y `autorizar` funcionan igual que en `create()`. A diferencia de `create()`, la
        respuesta trae el id del comprobante en `data.factura_id` (no en `data.id`).
        """
        fields.setdefault("concepto", 1)
        body: Dict[str, Any] = {"customer_id": customer_id, **fields}
        return self._client.post(
            f"{_BASE}/invoice/customer/", json_body=body, idempotency_key=idempotency_key
        )

    def credit_note(
        self,
        comprobante_asociado_id: str,
        items: Optional[List[Dict[str, Any]]] = None,
        **fields: Any,
    ) -> Any:
        """Emite una nota de crédito -- `POST /bill/receipts/credit-note/`.

        `comprobante_asociado_id` es el `id` del comprobante original, que debe
        estar aprobado. Cuánto acreditar se indica con UNO de estos campos:

        - `lineas=[{"linea": 1, "cantidad": 1}]`: devolución por renglón.
          `linea` es el índice (desde 0) del renglón del comprobante original y
          `cantidad` cuántas unidades se devuelven. El backend calcula neto e IVA
          de esos renglones.
        - `importe_a_acreditar=605.0`: un monto (bonificación, ajuste de precio).
        - `porcentaje_aplicar=50`: un porcentaje del comprobante (0 a 100].
        - Sin ninguno de los tres: anula el 100% del comprobante.

        `items` ya no se usa para devoluciones parciales: la API calcula las
        líneas de la nota a partir del original, y un `items` suelto que no
        coincida con el total de la nota se rechaza con 400.
        """
        body: Dict[str, Any] = {"comprobante_asociado_id": comprobante_asociado_id}
        if items is not None:
            body["items"] = items
        body.update(fields)
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
