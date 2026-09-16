from __future__ import annotations

import pytest

from yofacturo import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ScopeError,
    ServerError,
    ValidationError,
)


@pytest.mark.parametrize(
    "status,code,exc_type",
    [
        (401, "UNAUTHORIZED", AuthenticationError),
        (403, "FORBIDDEN", ScopeError),
        (404, "NOT_FOUND", NotFoundError),
        (400, "BAD_REQUEST", ValidationError),
        (400, "VALIDATION_ERROR", ValidationError),
        (422, "UNPROCESSABLE_ENTITY", ValidationError),
        (409, "CONFLICT", ConflictError),
        (429, "RATE_LIMITED", RateLimitError),
        (500, "INTERNAL_ERROR", ServerError),
        (503, "SERVICE_UNAVAILABLE", ServerError),
    ],
)
def test_status_maps_to_typed_exception(make_client, status, code, exc_type):
    client, _ = make_client(
        [(status, {}, {"success": False, "error": "boom", "code": code})], max_retries=0
    )
    with pytest.raises(exc_type) as exc_info:
        client.customers.get("x")
    err = exc_info.value
    assert err.status_code == status
    assert err.code == code
    assert err.message == "boom"


def test_scope_error_is_permission_error():
    assert PermissionError is ScopeError


def test_validation_error_carries_field_errors(make_client):
    client, _ = make_client(
        [
            (
                400,
                {},
                {
                    "success": False,
                    "error": "Validation failed",
                    "code": "VALIDATION_ERROR",
                    "errors": [{"field": "name", "message": "This field is required"}],
                },
            )
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        client.customers.create()
    assert exc_info.value.errors == [{"field": "name", "message": "This field is required"}]


def test_rate_limit_error_parses_retry_after_header(make_client):
    client, _ = make_client(
        [(429, {"Retry-After": "12"}, {"success": False, "error": "slow down", "code": "RATE_LIMITED"})],
        max_retries=0,
    )
    with pytest.raises(RateLimitError) as exc_info:
        client.customers.get("x")
    assert exc_info.value.retry_after == 12.0


def test_rate_limit_error_retry_after_is_none_without_header(make_client):
    client, _ = make_client(
        [(429, {}, {"success": False, "error": "slow down", "code": "RATE_LIMITED"})],
        max_retries=0,
    )
    with pytest.raises(RateLimitError) as exc_info:
        client.customers.get("x")
    assert exc_info.value.retry_after is None
