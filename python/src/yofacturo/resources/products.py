"""Productos -- `/products`. Scope: `products:read` / `products:write`."""

from __future__ import annotations

from typing import Any

from ._base import CrudResource


class ProductsResource(CrudResource):
    _base = "/products"

    def list(self, *, currency_aware: bool = True, **params: Any) -> Any:
        """Lista paginada -- `GET /products/list/`.

        Manda `currency_aware=1` por defecto: sin ese parametro la API omite los
        productos cuyo `price_currency` no es la moneda por defecto de la cuenta
        (un cliente viejo los leeria como pesos). Cada producto en otra moneda trae
        `price_currency`: mostrala y mandala como `currency` al vender. Pasa
        `currency_aware=False` para recibir solo los productos en la moneda por defecto.
        """
        if currency_aware:
            params["currency_aware"] = 1
        return super().list(**params)
