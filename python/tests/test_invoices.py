from __future__ import annotations


def test_create_invoice_posts_expected_body(make_client):
    client, transport = make_client(
        [(200, {}, {"success": True, "data": {"id": "abc", "estado": "pendiente"}})]
    )
    client.invoices.create(
        tipo_documento=99,
        numero_documento="0",
        razon_social="CONSUMIDOR FINAL",
        items=[{"descripcion": "Servicio", "cantidad": 1, "precio_unitario": 1000}],
        autorizar=True,
    )
    call = transport.last_call
    assert call["method"] == "POST"
    assert call["url"].endswith("/bill/receipts/invoice/")
    assert call["body"]["numero_documento"] == "0"
    assert call["body"]["autorizar"] is True


def test_create_sends_idempotency_key_header(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"id": "abc"}})])
    client.invoices.create(
        tipo_documento=99,
        numero_documento="0",
        items=[{"descripcion": "Servicio", "cantidad": 1, "precio_unitario": 1000}],
        idempotency_key="factura-2026-05-21-001",
    )
    assert transport.last_call["headers"]["Idempotency-Key"] == "factura-2026-05-21-001"


def test_create_for_customer_sets_customer_id(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"id": "abc"}})])
    client.invoices.create_for_customer(
        "cust_123",
        items=[{"descripcion": "Servicio", "cantidad": 1, "precio_unitario": 1000}],
        autorizar=False,
    )
    call = transport.last_call
    assert call["url"].endswith("/bill/receipts/invoice/")
    assert call["body"]["customer_id"] == "cust_123"
    assert call["body"]["autorizar"] is False


def test_credit_note_requires_comprobante_asociado_id(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"id": "nc_1"}})])
    client.invoices.credit_note(
        "factura_original_id",
        items=[{"descripcion": "Devolución", "cantidad": 1, "precio_unitario": 100}],
        motivo="Devolución parcial",
    )
    call = transport.last_call
    assert call["url"].endswith("/bill/receipts/credit-note/")
    assert call["body"]["comprobante_asociado_id"] == "factura_original_id"
    assert call["body"]["motivo"] == "Devolución parcial"


def test_debit_note_hits_debit_note_endpoint(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"id": "nd_1"}})])
    client.invoices.debit_note(
        "factura_original_id",
        items=[{"descripcion": "Interés", "cantidad": 1, "precio_unitario": 50}],
    )
    assert transport.last_call["url"].endswith("/bill/receipts/debit-note/")


def test_list_forwards_filters(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"items": []}})])
    client.invoices.list(page=1, per_page=20, estado="aprobado", tipo_comprobante=6)
    url = transport.last_call["url"]
    assert transport.last_call["method"] == "GET"
    assert "/bill/receipts/list/" in url
    assert "estado=aprobado" in url
    assert "tipo_comprobante=6" in url


def test_get_by_id(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"id": "abc"}})])
    client.invoices.get("abc")
    assert transport.last_call["url"].endswith("/bill/receipts/abc/")
    assert transport.last_call["method"] == "GET"


def test_authorize_sends_empty_body(make_client):
    client, transport = make_client(
        [(200, {}, {"success": True, "data": {"id": "abc", "cae": "123", "estado": "aprobado"}})]
    )
    result = client.invoices.authorize("abc")
    call = transport.last_call
    assert call["method"] == "POST"
    assert call["url"].endswith("/bill/receipts/authorize/abc/")
    assert call["body"] == {}
    assert result["data"]["cae"] == "123"


def test_cancel_without_motivo_sends_empty_body(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {}})])
    client.invoices.cancel("abc")
    call = transport.last_call
    assert call["url"].endswith("/bill/receipts/cancel/abc/")
    assert call["body"] == {}


def test_cancel_with_motivo(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {}})])
    client.invoices.cancel("abc", motivo="Emitido por error")
    assert transport.last_call["body"] == {"motivo": "Emitido por error"}


def test_supported_types(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": [1, 6, 11]})])
    client.invoices.supported_types()
    assert transport.last_call["url"].endswith("/bill/receipts/supported-types/")
    assert transport.last_call["method"] == "GET"
