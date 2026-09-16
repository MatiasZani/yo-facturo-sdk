from __future__ import annotations

import pytest

from yofacturo import RateLimitError, ServerError, YoFacturo, __version__


def test_requires_api_key():
    with pytest.raises(ValueError):
        YoFacturo(api_key="")


def test_sends_auth_and_user_agent_headers(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"items": []}})])
    client.products.list()
    headers = transport.last_call["headers"]
    assert headers["X-API-Key"] == "yf_live_test_token"
    assert headers["User-Agent"] == f"yofacturo-sdk-python/{__version__}"
    assert "yf_live_test_token" not in headers["User-Agent"]


def test_never_leaks_token_in_exception_str(make_client):
    client, _ = make_client(
        [(401, {}, {"success": False, "error": "Invalid token", "code": "UNAUTHORIZED"})]
    )
    with pytest.raises(Exception) as exc_info:
        client.products.list()
    assert "yf_live_test_token" not in str(exc_info.value)
    assert "yf_live_test_token" not in repr(exc_info.value)


def test_get_request_has_no_body(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {}})])
    client.customers.get("cust_1")
    assert transport.last_call["method"] == "GET"
    assert transport.last_call["body"] is None


def test_post_sends_json_body(make_client):
    client, transport = make_client([(201, {}, {"success": True, "data": {"_id": "p_1"}})])
    client.products.create(name="Producto A", base_price=100)
    call = transport.last_call
    assert call["method"] == "POST"
    assert call["body"] == {"name": "Producto A", "base_price": 100}
    assert call["headers"]["Content-Type"] == "application/json"


def test_query_params_drop_none_values(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"items": []}})])
    client.customers.list(page=2, per_page=None, search="acme")
    assert "page=2" in transport.last_call["url"]
    assert "per_page" not in transport.last_call["url"]
    assert "search=acme" in transport.last_call["url"]


def test_retries_on_429_then_succeeds(make_client):
    client, transport = make_client(
        [
            (429, {"Retry-After": "0"}, {"success": False, "error": "slow down", "code": "RATE_LIMITED"}),
            (200, {}, {"success": True, "data": {"items": []}}),
        ]
    )
    result = client.customers.list()
    assert result["success"] is True
    assert len(transport.calls) == 2


def test_retries_on_500_then_succeeds(make_client):
    client, transport = make_client(
        [
            (500, {}, {"success": False, "error": "boom", "code": "INTERNAL_ERROR"}),
            (503, {}, {"success": False, "error": "unavailable", "code": "SERVICE_UNAVAILABLE"}),
            (200, {}, {"success": True, "data": {"items": []}}),
        ]
    )
    result = client.customers.list()
    assert result["success"] is True
    assert len(transport.calls) == 3


def test_gives_up_after_max_retries(make_client):
    responses = [(429, {}, {"success": False, "error": "slow down", "code": "RATE_LIMITED"})] * 4
    client, transport = make_client(responses, max_retries=3)
    with pytest.raises(RateLimitError):
        client.customers.list()
    assert len(transport.calls) == 4  # intento inicial + 3 reintentos


def test_max_retries_zero_disables_retry(make_client):
    client, transport = make_client(
        [(500, {}, {"success": False, "error": "boom", "code": "INTERNAL_ERROR"})],
        max_retries=0,
    )
    with pytest.raises(ServerError):
        client.customers.list()
    assert len(transport.calls) == 1


def test_non_json_error_body_does_not_crash(make_client):
    client, transport = make_client([(502, {}, b"<html>Bad Gateway</html>")], max_retries=0)
    with pytest.raises(ServerError):
        client.customers.list()
