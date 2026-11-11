"""Recurso `client.sifen` (Paraguay): cada método pega al endpoint documentado en el OpenAPI."""

from __future__ import annotations

import pytest

from yofacturo import ConflictError, ServerError

CDC = "01800695631001001000000112026100710000000013"
OK = [(200, {}, {"success": True, "data": {}})]


def _call(make_client, invoke, responses=None):
    client, transport = make_client(responses or OK)
    invoke(client)
    return transport.last_call


def test_list_sends_only_the_filters_that_were_given(make_client):
    call = _call(
        make_client,
        lambda c: c.sifen.list(status="approved,approved_obs", caja="001-002", limit=50, cursor=None),
    )
    assert call["method"] == "GET"
    path, query = call["url"].split("?", 1)
    assert path.endswith("/bill/sifen/documents/")
    assert "status=approved%2Capproved_obs" in query
    assert "caja=001-002" in query
    assert "limit=50" in query
    assert "cursor" not in query and "tipo_de" not in query


def test_get_reads_the_document_by_cdc(make_client):
    call = _call(make_client, lambda c: c.sifen.get(CDC))
    assert call["method"] == "GET"
    assert call["url"].endswith(f"/bill/sifen/documents/{CDC}/")


def test_query_posts_an_empty_body_to_consulta(make_client):
    call = _call(make_client, lambda c: c.sifen.query(CDC))
    assert call["method"] == "POST"
    assert call["url"].endswith(f"/bill/sifen/documents/{CDC}/consulta/")
    assert call["body"] == {}


def test_events_reads_the_event_history(make_client):
    call = _call(make_client, lambda c: c.sifen.events(CDC))
    assert call["method"] == "GET"
    assert call["url"].endswith(f"/bill/sifen/documents/{CDC}/events/")


def test_void_sends_the_reason_and_the_idempotency_key_as_a_header(make_client):
    call = _call(make_client, lambda c: c.sifen.void(CDC, "Error de carga", idempotency_key="void-1"))
    assert call["method"] == "POST"
    assert call["url"].endswith(f"/bill/sifen/documents/{CDC}/void/")
    assert call["body"] == {"reason": "Error de carga"}
    assert call["headers"]["Idempotency-Key"] == "void-1"


def test_void_without_a_key_sends_no_idempotency_header(make_client):
    call = _call(make_client, lambda c: c.sifen.void(CDC, "Error de carga"))
    assert "Idempotency-Key" not in call["headers"]


ITEMS = [{"descripcion": "Ajuste", "importe": 11000, "tasa_iva": 10}]


def test_debit_note_preview_posts_items_and_motivo(make_client):
    call = _call(make_client, lambda c: c.sifen.debit_note_preview(CDC, ITEMS, motivo=8))
    assert call["url"].endswith(f"/bill/sifen/documents/{CDC}/debit-note/preview/")
    assert call["body"] == {"items": ITEMS, "motivo": 8}


def test_debit_note_drops_unset_optionals_and_forwards_the_key(make_client):
    call = _call(make_client, lambda c: c.sifen.debit_note(CDC, ITEMS, reason="Ajuste", idempotency_key="nde-1"))
    assert call["url"].endswith(f"/bill/sifen/documents/{CDC}/debit-note/")
    assert call["body"] == {"items": ITEMS, "reason": "Ajuste"}
    assert call["headers"]["Idempotency-Key"] == "nde-1"


def test_inutilizar_posts_the_range(make_client):
    call = _call(
        make_client,
        lambda c: c.sifen.inutilizar(
            tipo_de=1, establecimiento="001", punto_expedicion="001", desde=5, hasta=9, reason="Talonario perdido"
        ),
    )
    assert call["url"].endswith("/bill/sifen/inutilizaciones/")
    assert call["body"] == {
        "tipo_de": 1,
        "establecimiento": "001",
        "punto_expedicion": "001",
        "desde": 5,
        "hasta": 9,
        "reason": "Talonario perdido",
    }


def test_kude_routes(make_client):
    assert _call(make_client, lambda c: c.sifen.kude(CDC))["url"].endswith(f"/sales/sifen/documents/{CDC}/kude/")
    assert _call(make_client, lambda c: c.sifen.sale_kude("sale-1"))["url"].endswith("/sales/sale-1/sifen/kude/")


def test_send_email_defaults_to_the_customer_email(make_client):
    call = _call(make_client, lambda c: c.sifen.send_email(CDC))
    assert call["url"].endswith(f"/bill/sifen/documents/{CDC}/send-email/")
    assert call["body"] == {}
    assert _call(make_client, lambda c: c.sifen.send_email(CDC, "a@b.com"))["body"] == {"email": "a@b.com"}


def test_public_link_sends_the_expiry_only_when_given(make_client):
    call = _call(make_client, lambda c: c.sifen.public_link(CDC, 3600))
    assert call["url"].endswith(f"/bill/sifen/documents/{CDC}/public-link/")
    assert call["body"] == {"expires_in_seconds": 3600}
    assert _call(make_client, lambda c: c.sifen.public_link(CDC))["body"] == {}


def test_generate_invoice_posts_to_the_sale_route(make_client):
    call = _call(make_client, lambda c: c.sifen.generate_invoice("sale-1"))
    assert call["method"] == "POST"
    assert call["url"].endswith("/sales/generate_invoice/sale-1/")


def test_credit_note_requires_lineas_and_forwards_the_key(make_client):
    call = _call(
        make_client,
        lambda c: c.sifen.credit_note(
            "sale-1", "Devolución", lineas=[{"linea": 0, "cantidad": 1}], restore_stock=True, idempotency_key="nce-1"
        ),
    )
    assert call["url"].endswith("/sales/sale-1/credit_note/")
    assert call["body"] == {"reason": "Devolución", "lineas": [{"linea": 0, "cantidad": 1}], "restore_stock": True}
    assert call["headers"]["Idempotency-Key"] == "nce-1"


def test_credit_note_preview(make_client):
    call = _call(make_client, lambda c: c.sifen.credit_note_preview("sale-1", [{"linea": 0, "cantidad": 1}]))
    assert call["url"].endswith("/sales/sale-1/credit_note/preview/")
    assert call["body"] == {"lineas": [{"linea": 0, "cantidad": 1}]}


def test_receptor_event_merges_the_extra_fields(make_client):
    call = _call(make_client, lambda c: c.sifen.receptor_event("conformidad", CDC, total=True, reason="Ok"))
    assert call["url"].endswith("/received_invoices/sifen/events/")
    assert call["body"] == {"kind": "conformidad", "cdc": CDC, "total": True, "reason": "Ok"}


def test_readiness_and_catalogs_and_ruc_are_plain_gets(make_client):
    assert _call(make_client, lambda c: c.sifen.readiness())["url"].endswith("/bill/sifen/readiness/")
    assert _call(make_client, lambda c: c.sifen.catalogs())["url"].endswith("/bill/sifen/catalogs/")
    assert _call(make_client, lambda c: c.sifen.catalogs("note_motives"))["url"].endswith("/bill/sifen/catalogs/note_motives/")
    assert _call(make_client, lambda c: c.sifen.ruc("80069563-1"))["url"].endswith("/bill/sifen/ruc/80069563-1/")


def test_certificates_status_all_or_one_environment(make_client):
    assert _call(make_client, lambda c: c.sifen.certificates())["url"].endswith(
        "/bill/tax_info/taxpayer/sifen/certificates/"
    )
    assert _call(make_client, lambda c: c.sifen.certificates("prod"))["url"].endswith(
        "/bill/tax_info/taxpayer/sifen/certificates/prod/"
    )


def test_numbering_maps_pun_exp_to_the_wire_name(make_client):
    call = _call(make_client, lambda c: c.sifen.numbering(tipo_de=1, est="001", pun_exp="002"))
    path, query = call["url"].split("?", 1)
    assert path.endswith("/bill/sifen/numbering/")
    assert "punExp=002" in query and "est=001" in query and "tipo_de=1" in query


def test_seed_numbering_posts_last_used_and_dry_run(make_client):
    call = _call(make_client, lambda c: c.sifen.seed_numbering(120, pun_exp="002", dry_run=True))
    assert call["url"].endswith("/bill/sifen/numbering/seed/")
    assert call["body"] == {"last_used": 120, "punExp": "002", "dry_run": True}


def test_set_environment_conflict_raises_conflict_error_with_the_error_code(make_client):
    client, _ = make_client(
        [(409, {}, {"success": False, "error": "No prod certificate is uploaded", "code": "CONFLICT", "error_code": "certificate_missing"})]
    )
    with pytest.raises(ConflictError) as excinfo:
        client.sifen.set_environment("prod")
    assert excinfo.value.status_code == 409


def test_query_when_sifen_is_down_raises_server_error_without_retrying_forever(make_client):
    client, transport = make_client(
        [(503, {}, {"success": False, "error": "SIFEN is not reachable right now", "code": "SERVICE_UNAVAILABLE"})] * 4
    )
    with pytest.raises(ServerError):
        client.sifen.query(CDC)
    assert len(transport.calls) == 4


def test_create_posts_a_standalone_document_with_the_idempotency_key(make_client):
    call = _call(
        make_client,
        lambda c: c.sifen.create(
            [{"descripcion": "Servicio", "importe": 11000, "tasa_iva": 10}],
            receptor={"document_type": "ci", "document_number": "1234567", "name": "Maria"},
            sales_point_id=None,
            client_reference="order-7",
            idempotency_key="doc-1",
        ),
    )
    assert call["method"] == "POST"
    assert call["url"].endswith("/bill/sifen/documents/")
    assert call["body"] == {
        "tipo_de": 1,
        "items": [{"descripcion": "Servicio", "importe": 11000, "tasa_iva": 10}],
        "receptor": {"document_type": "ci", "document_number": "1234567", "name": "Maria"},
        "client_reference": "order-7",
    }
    assert call["headers"]["Idempotency-Key"] == "doc-1"


def test_diagnose_posts_an_empty_body(make_client):
    call = _call(make_client, lambda c: c.sifen.diagnose())
    assert call["method"] == "POST" and call["url"].endswith("/bill/sifen/diagnose/") and call["body"] == {}


def test_verify_caja_sends_only_what_was_given(make_client):
    call = _call(
        make_client, lambda c: c.sifen.verify_caja(establecimiento="001", punto_expedicion="002", check_ruc=False)
    )
    assert call["url"].endswith("/bill/sifen/verify-caja/")
    assert call["body"] == {"establecimiento": "001", "punto_expedicion": "002", "check_ruc": False}


def test_lote_reads_the_protocol(make_client):
    call = _call(make_client, lambda c: c.sifen.lote("987654321"))
    assert call["method"] == "GET" and call["url"].endswith("/bill/sifen/lotes/987654321/")


def test_types_and_validate_type(make_client):
    assert _call(make_client, lambda c: c.sifen.types())["url"].endswith("/bill/sifen/types/")
    call = _call(make_client, lambda c: c.sifen.validate_type(1, "standalone"))
    assert call["method"] == "POST" and call["url"].endswith("/bill/sifen/validate-type/")
    assert call["body"] == {"tipo_de": 1, "context": "standalone"}
    assert _call(make_client, lambda c: c.sifen.validate_type(4))["body"] == {"tipo_de": 4}
