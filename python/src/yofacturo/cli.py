"""Consola `yofacturo`: CLI fina sobre el SDK, pensada para agentes.

Todo el output es JSON en stdout. Ante un fallo el exit code es distinto de 0
y stdout trae `{"ok": false, "error": {...}}`. El token NUNCA se pasa por argv
ni se imprime: viene de `YOFACTURO_API_KEY` o del keyring (si está instalado).

    yofacturo login [--store]
    yofacturo invoice create -f factura.json [--idempotency-key K]
    yofacturo invoice get <id>
    yofacturo invoice link <id>
    yofacturo webhooks verify --secret-env YF_WEBHOOK_SECRET --payload-file body.raw --signature "t=..,v1=.."

Exit codes: 0 ok, 1 error de la API / firma inválida, 2 uso o input inválido,
3 falta el token.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import webhooks
from ._version import __version__
from .client import DEFAULT_BASE_URL, ENVIRONMENTS, YoFacturo, is_sandbox_key
from .errors import ApiError, YoFacturoError

ENV_API_KEY = "YOFACTURO_API_KEY"
KEYRING_SERVICE = "yofacturo"
KEYRING_USER = "api_key"

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_NO_TOKEN = 0, 1, 2, 3


class CliError(Exception):
    def __init__(self, message: str, *, exit_code: int = EXIT_ERROR, **extra: Any) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.extra = extra


class _JsonArgumentParser(argparse.ArgumentParser):
    """argparse que falla con JSON + exit 2 en vez de texto libre a stderr."""

    def error(self, message: str) -> Any:  # type: ignore[override]
        raise CliError(message, exit_code=EXIT_USAGE, kind="usage")


# -- token ------------------------------------------------------------------


def _keyring_module() -> Any:
    try:
        import keyring  # type: ignore[import-not-found]

        return keyring
    except Exception:  # keyring es opcional
        return None


def resolve_api_key(env: Optional[Dict[str, str]] = None) -> Tuple[Optional[str], Optional[str]]:
    """`(token, fuente)`; fuente = "env" | "keyring" | None."""
    environ = os.environ if env is None else env
    token = (environ.get(ENV_API_KEY) or "").strip()
    if token:
        return token, "env"
    kr = _keyring_module()
    if kr is not None:
        try:
            stored = kr.get_password(KEYRING_SERVICE, KEYRING_USER)
        except Exception:
            stored = None
        if stored:
            return stored.strip(), "keyring"
    return None, None


def _require_client(args: argparse.Namespace) -> YoFacturo:
    token, _ = resolve_api_key()
    if not token:
        raise CliError(
            f"Falta el token: definí la variable de entorno {ENV_API_KEY} (o corré `yofacturo login --store`).",
            exit_code=EXIT_NO_TOKEN,
            kind="auth",
        )
    return YoFacturo(api_key=token, base_url=args.base_url, environment=args.environment)


# -- comandos ---------------------------------------------------------------


def _read_json_file(path: str) -> Dict[str, Any]:
    try:
        raw = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
        data = json.loads(raw)
    except OSError as exc:
        raise CliError(f"No se pudo leer {path}: {exc.strerror or exc}", exit_code=EXIT_USAGE, kind="usage")
    except ValueError as exc:
        raise CliError(f"JSON inválido en {path}: {exc}", exit_code=EXIT_USAGE, kind="usage")
    if not isinstance(data, dict):
        raise CliError("El JSON debe ser un objeto", exit_code=EXIT_USAGE, kind="usage")
    return data


def _cmd_login(args: argparse.Namespace) -> Any:
    token, source = resolve_api_key()
    if not token:
        if not sys.stdin.isatty():
            token = sys.stdin.readline().strip()  # `echo $KEY | yofacturo login --store`
        else:
            token = getpass.getpass("YoFacturo API key (no se muestra): ").strip()
        source = "prompt"
    if not token:
        raise CliError("Token vacío", exit_code=EXIT_NO_TOKEN, kind="auth")
    client = YoFacturo(api_key=token, base_url=args.base_url, environment=args.environment)
    client.invoices.supported_types()  # verifica el token (levanta AuthenticationError si no sirve)
    stored = False
    if args.store:
        kr = _keyring_module()
        if kr is None:
            raise CliError("keyring no está instalado: pip install 'yofacturo[keyring]'", exit_code=EXIT_USAGE, kind="usage")
        kr.set_password(KEYRING_SERVICE, KEYRING_USER, token)
        stored = True
    return {"authenticated": True, "sandbox": is_sandbox_key(token), "source": source, "stored": stored}


def _cmd_invoice_create(args: argparse.Namespace) -> Any:
    body = _read_json_file(args.file)
    client = _require_client(args)
    return client.invoices.create(idempotency_key=args.idempotency_key, **body)


def _cmd_invoice_get(args: argparse.Namespace) -> Any:
    return _require_client(args).invoices.get(args.id)


def _cmd_invoice_link(args: argparse.Namespace) -> Any:
    return _require_client(args).invoices.link(args.id)


def _cmd_webhooks_verify(args: argparse.Namespace) -> Any:
    secret = os.environ.get(args.secret_env, "")
    if not secret:
        raise CliError(
            f"La variable de entorno {args.secret_env} está vacía o no existe",
            exit_code=EXIT_NO_TOKEN,
            kind="auth",
        )
    try:
        with open(args.payload_file, "rb") as fh:
            payload = fh.read()
    except OSError as exc:
        raise CliError(f"No se pudo leer {args.payload_file}: {exc.strerror or exc}", exit_code=EXIT_USAGE, kind="usage")
    tolerance: Optional[int] = None if args.tolerance < 0 else args.tolerance
    if not webhooks.verify_signature(secret, payload, args.signature, tolerance_seconds=tolerance):
        raise CliError("Firma inválida o fuera de tolerancia", kind="signature", valid=False)
    return {"valid": True}


# -- parser -----------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        prog="yofacturo",
        description="CLI de la API de YoFacturo (facturación ARCA/AFIP). Output JSON en stdout; "
        f"el token se lee de {ENV_API_KEY} o del keyring, nunca de argv.",
    )
    parser.add_argument("--version", action="version", version=f"yofacturo {__version__}")
    parser.add_argument("--base-url", default=os.environ.get("YOFACTURO_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument(
        "--environment",
        choices=ENVIRONMENTS,
        default=None,
        help='agrega "ambiente" a los bodies (usar "testing" con un token live para homologación ARCA)',
    )
    sub = parser.add_subparsers(dest="command", parser_class=_JsonArgumentParser, metavar="<command>")
    sub.required = True

    p = sub.add_parser("login", help="verifica el token y opcionalmente lo guarda en el keyring")
    p.add_argument("--store", action="store_true", help="guardar el token en el keyring del sistema")
    p.set_defaults(func=_cmd_login)

    inv = sub.add_parser("invoice", help="comprobantes").add_subparsers(
        dest="action", parser_class=_JsonArgumentParser, metavar="<action>"
    )
    inv.required = True
    p = inv.add_parser("create", help="emitir un comprobante desde un JSON")
    p.add_argument("-f", "--file", required=True, help="archivo JSON con el body ('-' = stdin)")
    p.add_argument("--idempotency-key", default=None, help="header Idempotency-Key (reintentos seguros)")
    p.set_defaults(func=_cmd_invoice_create)
    p = inv.add_parser("get", help="leer un comprobante (CAE, estado, afip_errors)")
    p.add_argument("id")
    p.set_defaults(func=_cmd_invoice_get)
    p = inv.add_parser("link", help="link público firmado del comprobante")
    p.add_argument("id")
    p.set_defaults(func=_cmd_invoice_link)

    wh = sub.add_parser("webhooks", help="webhooks").add_subparsers(
        dest="action", parser_class=_JsonArgumentParser, metavar="<action>"
    )
    wh.required = True
    p = wh.add_parser("verify", help="verificar la firma X-YF-Signature de una entrega")
    p.add_argument("--secret-env", required=True, help="NOMBRE de la variable de entorno con el secret")
    p.add_argument("--payload-file", required=True, help="body crudo recibido")
    p.add_argument("--signature", required=True, help="valor del header X-YF-Signature")
    p.add_argument("--tolerance", type=int, default=webhooks.DEFAULT_TOLERANCE_SECONDS, help="segundos; -1 = sin chequeo")
    p.set_defaults(func=_cmd_webhooks_verify)
    return parser


def _emit(obj: Any) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        result = args.func(args)
    except CliError as exc:
        _emit({"ok": False, "error": {"message": str(exc), **exc.extra}})
        return exc.exit_code
    except ApiError as exc:
        error: Dict[str, Any] = {"kind": "api", "message": exc.message, "status": exc.status_code}
        for attr in ("code", "errors", "retry_after"):
            value = getattr(exc, attr, None)
            if value is not None:
                error[attr] = value
        body = exc.response_body
        if isinstance(body, dict) and body.get("afip_errors") is not None:
            error["afip_errors"] = body["afip_errors"]
        _emit({"ok": False, "error": error})
        return EXIT_ERROR
    except YoFacturoError as exc:
        _emit({"ok": False, "error": {"kind": "client", "message": str(exc)}})
        return EXIT_ERROR
    except SystemExit as exc:  # --help / --version
        return int(exc.code or 0)
    _emit({"ok": True, "data": result})
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
