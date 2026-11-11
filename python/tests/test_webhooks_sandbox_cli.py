"""Tests de 0.3.0: webhooks, sandbox/environment, invoices.link y la CLI."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from yofacturo import YoFacturo, is_sandbox_key, webhooks
from yofacturo import cli

SECRET = "whsec_test"
BODY = b'{"id":"evt_1","event":"invoice.authorized","data":{"id":"abc"}}'
NOW = 1_760_000_000


def _sig(ts: int = NOW, body: bytes = BODY, secret: str = SECRET) -> str:
    # Algoritmo del firmador saliente de la API, calculado a mano.
    hexd = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={ts},v1={hexd}"


# -- webhooks ---------------------------------------------------------------


def test_verify_accepts_valid_signature():
    assert webhooks.verify_signature(SECRET, BODY, _sig(), now=NOW + 10)
    assert webhooks.verify_signature(SECRET, BODY.decode(), _sig(), now=NOW)  # str body


def test_build_header_matches_api_algorithm():
    assert webhooks.build_signature_header(SECRET, NOW, BODY) == _sig()


@pytest.mark.parametrize(
    "header",
    [None, "", "garbage", "t=abc,v1=ff", "v1=" + "0" * 64, f"t={NOW}", f"t={NOW},v1={'0' * 64}"],
)
def test_verify_rejects_bad_headers(header):
    assert webhooks.verify_signature(SECRET, BODY, header, now=NOW) is False


def test_verify_rejects_tampered_body_and_wrong_secret():
    assert not webhooks.verify_signature(SECRET, BODY + b" ", _sig(), now=NOW)
    assert not webhooks.verify_signature("otro", BODY, _sig(), now=NOW)


def test_verify_replay_tolerance():
    assert not webhooks.verify_signature(SECRET, BODY, _sig(), now=NOW + 301)
    assert webhooks.verify_signature(SECRET, BODY, _sig(), now=NOW + 300)
    assert webhooks.verify_signature(SECRET, BODY, _sig(), now=NOW + 99999, tolerance_seconds=None)


def test_construct_event():
    assert webhooks.construct_event(SECRET, BODY, _sig(), now=NOW)["event"] == "invoice.authorized"
    with pytest.raises(ValueError):
        webhooks.construct_event(SECRET, BODY, "t=1,v1=00", now=NOW)


# -- sandbox / environment / idempotency --------------------------------------


def test_is_sandbox_key():
    assert is_sandbox_key("yf_test_abc")
    assert not is_sandbox_key("yf_live_abc")
    assert not is_sandbox_key(None)


def test_client_is_sandbox_property(make_client):
    client, _ = make_client([])
    assert client.is_sandbox is False
    assert YoFacturo(api_key="yf_test_x").is_sandbox is True


def test_environment_injects_ambiente_without_overriding(make_client):
    client, transport = make_client([(200, {}, {"success": True})] * 2, environment="testing")
    client.invoices.create(items=[])
    assert transport.calls[0]["body"]["ambiente"] == "testing"
    client.invoices.create(items=[], ambiente="production")
    assert transport.calls[1]["body"]["ambiente"] == "production"


def test_no_environment_leaves_body_untouched(make_client):
    client, transport = make_client([(200, {}, {"success": True})])
    client.invoices.create(items=[])
    assert "ambiente" not in transport.calls[0]["body"]


def test_invalid_environment_rejected():
    with pytest.raises(ValueError):
        YoFacturo(api_key="k", environment="staging")


def test_idempotency_key_header(make_client):
    client, transport = make_client([(200, {}, {"success": True})])
    client.invoices.create(idempotency_key="k-1", items=[])
    assert transport.calls[0]["headers"]["Idempotency-Key"] == "k-1"


def test_invoices_link(make_client):
    client, transport = make_client([(200, {}, {"success": True, "data": {"url": "u"}})])
    client.invoices.link("abc")
    assert transport.calls[0]["method"] == "POST"
    assert transport.calls[0]["url"].endswith("/bill/receipts/abc/public-link/")


# -- CLI --------------------------------------------------------------------


@pytest.fixture
def fake_api(monkeypatch):
    calls = []

    def factory(responder):
        def _transport(method, url, headers, body, timeout):
            calls.append({"method": method, "url": url, "headers": dict(headers), "body": json.loads(body) if body else None})
            status, payload = responder(method, url)
            return status, {}, json.dumps(payload).encode()

        real = cli.YoFacturo

        def _client(**kw):
            return real(transport=_transport, sleep=lambda s: None, **kw)

        monkeypatch.setattr(cli, "YoFacturo", _client)
        return calls

    return factory


def _run(capsys, argv):
    code = cli.main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_help_exits_zero(capsys):
    assert cli.main(["--help"]) == 0
    assert "invoice" in capsys.readouterr().out


def test_missing_token_is_json_error(monkeypatch, capsys):
    monkeypatch.delenv("YOFACTURO_API_KEY", raising=False)
    monkeypatch.setattr(cli, "_keyring_module", lambda: None)
    code, out = _run(capsys, ["invoice", "get", "abc"])
    assert code == cli.EXIT_NO_TOKEN
    assert out["ok"] is False and out["error"]["kind"] == "auth"


def test_usage_error_is_json(capsys):
    code, out = _run(capsys, ["invoice"])
    assert code == cli.EXIT_USAGE and out["ok"] is False


def test_invoice_create_get_link(monkeypatch, capsys, tmp_path, fake_api):
    monkeypatch.setenv("YOFACTURO_API_KEY", "yf_test_secret")
    calls = fake_api(lambda m, u: (200, {"success": True, "data": {"id": "abc"}}))
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"items": [{"descripcion": "x", "cantidad": 1, "precio_unitario": 10}]}))

    code, out = _run(capsys, ["--environment", "testing", "invoice", "create", "-f", str(f), "--idempotency-key", "K1"])
    assert code == 0 and out == {"ok": True, "data": {"success": True, "data": {"id": "abc"}}}
    assert calls[0]["headers"]["Idempotency-Key"] == "K1"
    assert calls[0]["headers"]["X-API-Key"] == "yf_test_secret"
    assert calls[0]["body"]["ambiente"] == "testing"

    assert _run(capsys, ["invoice", "get", "abc"])[0] == 0
    assert calls[1]["url"].endswith("/bill/receipts/abc/")
    assert _run(capsys, ["invoice", "link", "abc"])[0] == 0
    assert calls[2]["url"].endswith("/bill/receipts/abc/public-link/")


def test_api_error_gives_nonzero_and_afip_errors(monkeypatch, capsys, tmp_path, fake_api):
    monkeypatch.setenv("YOFACTURO_API_KEY", "yf_live_secret")
    fake_api(lambda m, u: (400, {"success": False, "error": "rechazado", "code": "VALIDATION_ERROR",
                                 "afip_errors": [{"code": 10016, "msg": "x"}]}))
    f = tmp_path / "x.json"
    f.write_text("{}")
    code, out = _run(capsys, ["invoice", "create", "-f", str(f)])
    assert code == cli.EXIT_ERROR
    assert out["error"]["status"] == 400 and out["error"]["afip_errors"][0]["code"] == 10016
    assert "yf_live_secret" not in json.dumps(out)


def test_invoice_create_bad_file(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("YOFACTURO_API_KEY", "k")
    code, out = _run(capsys, ["invoice", "create", "-f", str(tmp_path / "missing.json")])
    assert code == cli.EXIT_USAGE and out["ok"] is False


def test_webhooks_verify_cli(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("YF_SECRET", SECRET)
    p = tmp_path / "body.raw"
    p.write_bytes(BODY)
    argv = ["webhooks", "verify", "--secret-env", "YF_SECRET", "--payload-file", str(p), "--signature", _sig()]
    code, out = _run(capsys, argv + ["--tolerance", "-1"])
    assert code == 0 and out["data"] == {"valid": True}
    code, out = _run(capsys, argv)  # NOW de 2025: fuera de tolerancia
    assert code == cli.EXIT_ERROR and out["error"]["valid"] is False
    monkeypatch.delenv("YF_SECRET")
    assert _run(capsys, argv)[0] == cli.EXIT_NO_TOKEN


def test_login_verifies_token_without_echo(monkeypatch, capsys, fake_api):
    monkeypatch.setenv("YOFACTURO_API_KEY", "yf_test_zzz")
    fake_api(lambda m, u: (200, {"success": True, "data": []}))
    code, out = _run(capsys, ["login"])
    assert code == 0
    assert out["data"] == {"authenticated": True, "sandbox": True, "source": "env", "stored": False}
    assert "yf_test_zzz" not in json.dumps(out)


def test_login_store_without_keyring(monkeypatch, capsys, fake_api):
    monkeypatch.setenv("YOFACTURO_API_KEY", "yf_live_zzz")
    monkeypatch.setattr(cli, "_keyring_module", lambda: None)
    fake_api(lambda m, u: (200, {"success": True}))
    code, out = _run(capsys, ["login", "--store"])
    assert code == cli.EXIT_USAGE and "keyring" in out["error"]["message"]


def test_resolve_key_prefers_env_then_keyring(monkeypatch):
    class KR:
        @staticmethod
        def get_password(s, u):
            return " from_kr "

    monkeypatch.setattr(cli, "_keyring_module", lambda: KR)
    assert cli.resolve_api_key({"YOFACTURO_API_KEY": "e"}) == ("e", "env")
    assert cli.resolve_api_key({}) == ("from_kr", "keyring")
