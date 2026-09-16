"""Productos -- `/products`. Scope: `products:read` / `products:write`."""

from __future__ import annotations

from ._base import CrudResource


class ProductsResource(CrudResource):
    _base = "/products"
