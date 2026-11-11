"""CRUD estándar compartido por customers, products, sales, services, rentals, appointments y subscription_plans (ver /dev/conventions/)."""

from __future__ import annotations

import pytest

RESOURCES = [
    "customers",
    "products",
    "sales",
    "services",
    "rentals",
    "appointments",
    "subscription_plans",
]
BASES = {
    "customers": "/customers",
    "products": "/products",
    "sales": "/sales",
    "services": "/services",
    "rentals": "/rentals",
    "appointments": "/appointments",
    "subscription_plans": "/subscription-plans",
}
# Recursos con listados multi-moneda: list() manda currency_aware=1 por defecto.
CURRENCY_AWARE = {"products", "services", "rentals"}


@pytest.mark.parametrize("resource_name", RESOURCES)
def test_list(make_client, resource_name):
    client, transport = make_client([(200, {}, {"success": True, "data": {"items": [], "total": 0}})])
    getattr(client, resource_name).list(page=1, per_page=10)
    call = transport.last_call
    assert call["method"] == "GET"
    # products.list() manda currency_aware=1 por defecto (ver test_products_list_currency_aware).
    aware = "&currency_aware=1" if resource_name in CURRENCY_AWARE else ""
    assert call["url"].endswith(f"{BASES[resource_name]}/list/?page=1&per_page=10{aware}")


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


def test_products_list_currency_aware_default_and_opt_out(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"items": []}})] * 3)
    client.products.list()
    assert transport.last_call["url"].endswith("/products/list/?currency_aware=1")
    client.products.list(currency_aware=False, page=2)
    assert transport.last_call["url"].endswith("/products/list/?page=2")
    client.sales.list()
    assert "currency_aware" not in transport.last_call["url"]


def test_create_forwards_price_currency_and_currency(make_client):
    client, transport = make_client([(201, {}, {"success": True, "data": {"_id": "n"}})] * 2)
    client.products.create(name="Pen", base_price=10, price_currency="USD")
    assert transport.last_call["body"] == {"name": "Pen", "base_price": 10, "price_currency": "USD"}
    client.sales.create(items=[{"product_id": "p"}], currency="USD")
    assert transport.last_call["body"]["currency"] == "USD"



@pytest.mark.parametrize("resource_name", ["services", "rentals"])
def test_catalog_list_currency_aware_default_and_opt_out(make_client, resource_name):
    client, transport = make_client([(200, {}, {"success": True, "data": {"items": []}})] * 2)
    res = getattr(client, resource_name)
    res.list()
    assert transport.last_call["url"].endswith(f"{BASES[resource_name]}/list/?currency_aware=1")
    res.list(currency_aware=False, page=2)
    assert transport.last_call["url"].endswith(f"{BASES[resource_name]}/list/?page=2")


@pytest.mark.parametrize("resource_name", ["appointments", "subscription_plans"])
def test_plain_list_does_not_send_currency_aware(make_client, resource_name):
    client, transport = make_client([(200, {}, {"success": True, "data": {"items": []}})])
    getattr(client, resource_name).list()
    assert "currency_aware" not in transport.last_call["url"]
