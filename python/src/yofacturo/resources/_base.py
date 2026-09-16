"""Mixin con el patrón CRUD estándar de la API (ver /dev/conventions/)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ..client import YoFacturo


class CrudResource:
    #: prefijo del recurso, ej. "/customers". Lo define cada subclase.
    _base = ""

    def __init__(self, client: "YoFacturo") -> None:
        self._client = client

    def list(
        self,
        *,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        sort_dir: Optional[int] = None,
        fields: Optional[str] = None,
        **extra: Any,
    ) -> Any:
        """Lista paginada -- `GET {base}/list/`."""
        params: Dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "search": search,
            "sort": sort,
            "sort_dir": sort_dir,
            "fields": fields,
            **extra,
        }
        return self._client.get(f"{self._base}/list/", params=params)

    def get(self, resource_id: str) -> Any:
        """Un registro por su id -- `GET {base}/{id}/`."""
        return self._client.get(f"{self._base}/{resource_id}/")

    def create(self, *, idempotency_key: Optional[str] = None, **fields: Any) -> Any:
        """Crea un registro -- `POST {base}/`.

        `idempotency_key` es opcional (ver `YoFacturo.post`); la API lo
        soporta hoy en `/products/` y `/sales/`.
        """
        return self._client.post(f"{self._base}/", json_body=fields, idempotency_key=idempotency_key)

    def update(self, resource_id: str, **fields: Any) -> Any:
        """Actualiza los campos enviados -- `PUT {base}/{id}/`.

        Los campos omitidos se mantienen sin cambios; para borrar el valor
        de un campo mandá `None` explícitamente.
        """
        return self._client.put(f"{self._base}/{resource_id}/", json_body=fields)

    def delete(self, resource_id: str) -> Any:
        """Elimina (baja lógica) -- `DELETE {base}/{id}/`."""
        return self._client.delete(f"{self._base}/{resource_id}/")
