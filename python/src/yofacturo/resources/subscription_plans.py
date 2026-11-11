"""Planes de suscripcion -- `/subscription-plans`. Scope: `recurring:read` / `recurring:write`."""

from __future__ import annotations

from ._base import CrudResource


class SubscriptionPlansResource(CrudResource):
    _base = "/subscription-plans"
