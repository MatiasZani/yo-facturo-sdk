"""Ventas -- `/sales`. Scope: `sales:read` / `sales:write`."""

from __future__ import annotations

from ._base import CrudResource


class SalesResource(CrudResource):
    _base = "/sales"
