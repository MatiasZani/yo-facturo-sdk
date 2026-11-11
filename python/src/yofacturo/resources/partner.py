"""Cuentas API partner -- `/partner`.

Solo para cuentas con contrato partner (cualquier otra recibe 403 con
`error_code: "API_PARTNER_REQUIRED"`). Flujo: `taxpayers.create(...)` registra
el CUIT de tu usuario final, el usuario delega WSFE al CUIT de YoFacturo,
`verify_delegation(id)` lo confirma y después se factura con
`client.invoices.create(taxpayer_id=<id>, ...)`.

Scopes: `taxpayers:read` para leer, `taxpayers:write` para registrar, dar de
baja y verificar la delegación (solo los ve una cuenta partner).
Guía: https://yo-facturo.com/dev/ (sección «Cuentas API partner»).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ..client import YoFacturo

_BASE = "/partner"


def _compact(**fields: Any) -> Dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


class PartnerResource:
    def __init__(self, client: "YoFacturo") -> None:
        self._client = client

    def create_taxpayer(
        self,
        tax_id: str,
        *,
        tax_condition: Optional[str] = None,
        punto_venta: Optional[str] = None,
        business_name: Optional[str] = None,
        **extra: Any,
    ) -> Any:
        """Registra el CUIT de un usuario final -- `POST /partner/taxpayers/` (`taxpayers:write`).

        Devuelve el contribuyente; su `id` es el `taxpayer_id` para facturar.
        Errores: `ValidationError` con `API_PARTNER_TAXPAYER_CUIT_INVALID`,
        `ConflictError` con `API_PARTNER_TAXPAYER_DUPLICATE` o
        `API_PARTNER_TAXPAYER_CUIT_CLAIMED`.
        """
        body = {
            "tax_id": tax_id,
            **_compact(tax_condition=tax_condition, punto_venta=punto_venta, business_name=business_name),
            **extra,
        }
        return self._client.post(f"{_BASE}/taxpayers/", json_body=body)

    def list_taxpayers(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        q: Optional[str] = None,
    ) -> Any:
        """Lista los CUIT activos -- `GET /partner/taxpayers/` (`taxpayers:read`).

        Paginación por cursor: pasá `data.next_cursor` como `cursor` hasta que
        venga `None`. `q` busca por CUIT o razón social; `limit` máx. 500.
        """
        return self._client.get(f"{_BASE}/taxpayers/", params=_compact(limit=limit, cursor=cursor, q=q))

    def get_taxpayer(self, taxpayer_id: str) -> Any:
        """Un CUIT registrado -- `GET /partner/taxpayers/{taxpayer_id}/` (`taxpayers:read`)."""
        return self._client.get(f"{_BASE}/taxpayers/{taxpayer_id}/")

    def remove_taxpayer(self, taxpayer_id: str) -> Any:
        """Baja lógica de un CUIT -- `DELETE /partner/taxpayers/{taxpayer_id}/` (`taxpayers:write`).

        No se pueden emitir comprobantes nuevos con él; los emitidos conservan su historial.
        """
        return self._client.delete(f"{_BASE}/taxpayers/{taxpayer_id}/")

    def verify_delegation(self, taxpayer_id: str) -> Any:
        """Verifica la delegación WSFE de un CUIT -- `POST /partner/taxpayers/{taxpayer_id}/verify-delegation/`.

        `data.delegation_verified` es `True`, `False` o `None` (ARCA no contestó:
        reintentá). Scope `taxpayers:write`; máx. 60 por minuto.
        """
        return self._client.post(f"{_BASE}/taxpayers/{taxpayer_id}/verify-delegation/", json_body={})

    def usage(self) -> Any:
        """CUIT activos del período y estimado en ARS -- `GET /partner/usage/` (`taxpayers:read`)."""
        return self._client.get(f"{_BASE}/usage/")
