"""CRUD estándar compartido por customers, products y sales (ver /dev/conventions/)."""

from __future__ import annotations

import pytest

RESOURCES = ["customers", "products", "sales"]
BASES = {"customers": "/customers", "products": "/products", "sales": "/sales"}


@pytest.mark.parametrize("resource_name", RESOURCES)
def test_list(make_client, resource_name):
    client, transport = make_client([(200, {}, {"success": True, "data": {"items": [], "total": 0}})])
    getattr(client, resource_name).list(page=1, per_page=10)
    call = transport.last_call
    assert call["method"] == "GET"
    assert call["url"].endswith(f"{BASES[resource_name]}/list/?page=1&per_page=10")


@pytest.mark.parametrize("resource_name", RESOURCES)
def test_get(make_client, resource_name):
    client, transport = make_client([(200, {}, {"success": True, "data": {"_id": "x"}})])
    getattr(client, resource_name).get("x")
    call = transport.last_call
    assert call["method"] == "GET"
    assert call["url"].endswith(f"{BASES[resource_name]}/x/")


@pytest.mark.parametrize("resource_name", RESOURCES)
def test_create(make_client, resource_name):
    client, transport = make_client([(201, {}, {"success": True, "data": {"_id": "new"}})])
    getattr(client, resource_name).create(name="Test")
    call = transport.last_call
    assert call["method"] == "POST"
    assert call["url"].endswith(f"{BASES[resource_name]}/")
    assert call["body"] == {"name": "Test"}


@pytest.mark.parametrize("resource_name", ["products", "sales"])
def test_create_supports_idempotency_key(make_client, resource_name):
    client, transport = make_client([(201, {}, {"success": True, "data": {"_id": "new"}})])
    getattr(client, resource_name).create(name="Test", idempotency_key="op-001")
    assert transport.last_call["headers"]["Idempotency-Key"] == "op-001"


@pytest.mark.parametrize("resource_name", RESOURCES)
def test_update_is_partial(make_client, resource_name):
    client, transport = make_client([(200, {}, {"success": True, "data": {"_id": "x"}})])
    getattr(client, resource_name).update("x", price=1500, description=None)
    call = transport.last_call
    assert call["method"] == "PUT"
    assert call["url"].endswith(f"{BASES[resource_name]}/x/")
    # None explícito viaja en el body -- así se borra un campo (ver conventions).
    assert call["body"] == {"price": 1500, "description": None}


@pytest.mark.parametrize("resource_name", RESOURCES)
def test_delete(make_client, resource_name):
    client, transport = make_client([(200, {}, {"success": True, "data": {"deleted": True}})])
    getattr(client, resource_name).delete("x")
    call = transport.last_call
    assert call["method"] == "DELETE"
    assert call["url"].endswith(f"{BASES[resource_name]}/x/")
    assert call["body"] is None
