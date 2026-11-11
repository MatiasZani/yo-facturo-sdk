"""Recurso `client.partner` (cuentas API partner): cada método pega al endpoint documentado en el OpenAPI."""

from __future__ import annotations

import pytest

from yofacturo import ConflictError, PermissionError, ValidationError

OK = [(200, {}, {"success": True, "data": {}})]
TP = "6650f2c1a1b2c3d4e5f60718"


def _call(make_client, invoke, responses=None):
    client, transport = make_client(responses or OK)
    invoke(client)
    return transport.last_call


def test_create_taxpayer_posts_tax_id_and_only_the_given_fields(make_client):
    call = _call(
        make_client,
        lambda c: c.partner.create_taxpayer("20111111112", tax_condition="monotributo", punto_venta="2"),
    )
    assert call["method"] == "POST"
    assert call["url"].endswith("/partner/taxpayers/")
    assert call["body"] == {"tax_id": "20111111112", "tax_condition": "monotributo", "punto_venta": "2"}


def test_list_taxpayers_sends_only_the_given_params(make_client):
    call = _call(make_client, lambda c: c.partner.list_taxpayers(limit=100, q="cliente"))
    assert call["method"] == "GET"
    path, query = call["url"].split("?", 1)
    assert path.endswith("/partner/taxpayers/")
    assert "limit=100" in query and "q=cliente" in query and "cursor" not in query


def test_get_remove_verify_and_usage_hit_their_routes(make_client):
    get = _call(make_client, lambda c: c.partner.get_taxpayer(TP))
    assert (get["method"], get["url"].endswith(f"/partner/taxpayers/{TP}/")) == ("GET", True)
    rm = _call(make_client, lambda c: c.partner.remove_taxpayer(TP))
    assert (rm["method"], rm["url"].endswith(f"/partner/taxpayers/{TP}/")) == ("DELETE", True)
    ver = _call(make_client, lambda c: c.partner.verify_delegation(TP))
    assert ver["method"] == "POST"
    assert ver["url"].endswith(f"/partner/taxpayers/{TP}/verify-delegation/")
    usage = _call(make_client, lambda c: c.partner.usage())
    assert (usage["method"], usage["url"].endswith("/partner/usage/")) == ("GET", True)


def test_invoices_create_forwards_taxpayer_id(make_client):
    call = _call(make_client, lambda c: c.invoices.create(taxpayer_id=TP, punto_venta=2, items=[]))
    assert call["url"].endswith("/bill/receipts/invoice/")
    assert call["body"]["taxpayer_id"] == TP


def test_partner_required_is_a_permission_error(make_client):
    body = {"success": False, "error": "only partners", "code": "FORBIDDEN", "error_code": "API_PARTNER_REQUIRED"}
    client, _ = make_client([(403, {}, body)])
    with pytest.raises(PermissionError):
        client.partner.usage()


def test_taxpayer_errors_map_to_validation_and_conflict(make_client):
    client, _ = make_client([(400, {}, {"success": False, "error": "Invalid CUIT", "code": "BAD_REQUEST"})])
    with pytest.raises(ValidationError):
        client.partner.create_taxpayer("1")
    client, _ = make_client([(409, {}, {"success": False, "error": "dup", "code": "CONFLICT"})])
    with pytest.raises(ConflictError):
        client.partner.create_taxpayer("20111111112")
