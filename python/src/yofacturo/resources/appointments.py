"""Turnos -- `/appointments`. Scope: `appointments:read` / `appointments:write`."""

from __future__ import annotations

from ._base import CrudResource


class AppointmentsResource(CrudResource):
    _base = "/appointments"
