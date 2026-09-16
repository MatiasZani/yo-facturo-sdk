"""Clientes -- `/customers`. Scope: `customers:read` / `customers:write`."""

from __future__ import annotations

from ._base import CrudResource


class CustomersResource(CrudResource):
    _base = "/customers"
