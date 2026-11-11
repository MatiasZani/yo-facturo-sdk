"""Alquileres -- `/rentals`. Scope: `rentals:read` / `rentals:write`."""

from __future__ import annotations

from typing import Any

from ._base import CrudResource


class RentalsResource(CrudResource):
    _base = "/rentals"

    def list(self, *, currency_aware: bool = True, **params: Any) -> Any:
        """Lista paginada -- `GET /rentals/list/`.

        Manda `currency_aware=1` por defecto: sin ese parametro la API omite los
        registros cuyo `price_currency` no es la moneda por defecto de la cuenta (un
        cliente viejo los leeria como pesos). Cada registro en otra moneda trae
        `price_currency`: mostrala y mandala como `currency` al vender. Pasa
        `currency_aware=False` para recibir solo los de la moneda por defecto.
        """
        if currency_aware:
            params["currency_aware"] = 1
        return super().list(**params)
