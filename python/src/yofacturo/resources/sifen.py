"""Facturación electrónica de Paraguay (SIFEN) -- `/bill/sifen`.

La emisión sale por `client.sales.create(..., request_fiscal_document=True)` (o
`generate_invoice()` sobre una venta existente) y es asíncrona: la respuesta
no trae el CDC, hay que releer la venta (`client.sales.get(id)`, campo
`fiscal`) o este recurso (`get(cdc)`) hasta que `status` sea `approved`, o
suscribirse a los webhooks `invoice.authorized` / `invoice.rejected` /
`invoice.cancelled` (`system: "sifen"`).

Scope requerido: `invoices:read` para leer, `invoices:write` para operar
documentos, `accounting:read|write` para la configuración (certificados,
ambiente, numeración), `received_invoices:write` para los eventos del
receptor. Un token `yf_test_*` lee todo pero nunca transmite a SIFEN (409).
Guía completa: https://yo-facturo.com/dev/paraguay-sifen/

Fuera del SDK: la subida del certificado PKCS#12 (`multipart/form-data`) y la
descarga del XML firmado (`application/xml`); usá HTTP directo, ver la guía.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ..client import YoFacturo

_BASE = "/bill/sifen"


def _compact(**fields: Any) -> Dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


class SifenResource:
    def __init__(self, client: "YoFacturo") -> None:
        self._client = client

    # -- documentos -----------------------------------------------------

    def list(
        self,
        *,
        tipo_de: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sale_id: Optional[str] = None,
        cdc: Optional[str] = None,
        caja: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        **extra: Any,
    ) -> Any:
        """Lista documentos SIFEN, el más nuevo primero -- `GET /bill/sifen/documents/`.

        `status` acepta varios estados separados por coma (`"approved,approved_obs"`);
        `caja` es `"<establecimiento>-<punto>"` (`"001-002"`). La paginación es por
        cursor: pasá `data.next_cursor` como `cursor` hasta que venga `None`.
        """
        params: Dict[str, Any] = {
            "tipo_de": tipo_de,
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
            "sale_id": sale_id,
            "cdc": cdc,
            "caja": caja,
            "limit": limit,
            "cursor": cursor,
            **extra,
        }
        return self._client.get(f"{_BASE}/documents/", params=params)

    def create(
        self,
        items: List[Dict[str, Any]],
        *,
        receptor: Optional[Dict[str, Any]] = None,
        tipo_de: int = 1,
        condicion: Optional[str] = None,
        pago_tipo: Optional[int] = None,
        plazo_dias: Optional[int] = None,
        sales_point_id: Optional[str] = None,
        establecimiento: Optional[str] = None,
        punto_expedicion: Optional[str] = None,
        info_emisor: Optional[str] = None,
        client_reference: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Emite una factura electrónica (FE, `tipo_de` 1) SIN venta -- `POST /bill/sifen/documents/`.

        Cada ítem: `descripcion`, `cantidad` (default 1), `precio_unitario` o
        `importe` (BRUTO, IVA incluido, guaraníes enteros) y `tasa_iva` (10, 5 o 0
        exento): el backend calcula base, IVA y total. `receptor`:
        `{"document_type": "ruc"|"ci"|"none", "document_number", "name", "email", "phone"}`.
        Caja: `sales_point_id` o `establecimiento` + `punto_expedicion` (default los
        del contribuyente). `client_reference` repite el mismo documento sin numerar
        otro. Es asíncrona: la respuesta trae el CDC en estado `signed`; leé
        `get(cdc)` hasta `approved`. Solo la FE (1); las notas usan `debit_note` y
        `credit_note`.
        """
        body = {
            "tipo_de": tipo_de,
            "items": items,
            **_compact(
                receptor=receptor,
                condicion=condicion,
                pago_tipo=pago_tipo,
                plazo_dias=plazo_dias,
                sales_point_id=sales_point_id,
                establecimiento=establecimiento,
                punto_expedicion=punto_expedicion,
                info_emisor=info_emisor,
                client_reference=client_reference,
            ),
        }
        return self._client.post(f"{_BASE}/documents/", json_body=body, idempotency_key=idempotency_key)

    def get(self, cdc: str) -> Any:
        """Obtiene un documento por su CDC (44 dígitos) -- `GET /bill/sifen/documents/{cdc}/`.

        Trae `status`, número, timbrado, totales, QR, protocolo, `sifen_messages`
        (cada `dCodRes`/`dMsgRes` que contestó SIFEN: el motivo de un rechazo) y
        los eventos del documento.
        """
        return self._client.get(f"{_BASE}/documents/{cdc}/")

    def query(self, cdc: str) -> Any:
        """Consulta el documento en vivo a SIFEN (siConsDE) -- `POST /bill/sifen/documents/{cdc}/consulta/`.

        Actualiza el estado local si SIFEN ya lo aprobó. Si SIFEN no responde
        levanta `ServerError` (503) y el estado local no cambia. Límite: 30 por minuto.
        """
        return self._client.post(f"{_BASE}/documents/{cdc}/consulta/", json_body={})

    def events(self, cdc: str) -> Any:
        """Historial de eventos de un documento -- `GET /bill/sifen/documents/{cdc}/events/`."""
        return self._client.get(f"{_BASE}/documents/{cdc}/events/")

    def void(self, cdc: str, reason: str, *, idempotency_key: Optional[str] = None) -> Any:
        """Anula un documento -- `POST /bill/sifen/documents/{cdc}/void/`.

        Según el estado: cancelación (FE aprobada hace menos de 48 h), nota de
        crédito por el saldo (fuera de ventana), o inutilización (número nunca
        aprobado). `data.action` dice cuál se hizo. `reason`: 5 a 500 caracteres.
        """
        return self._client.post(
            f"{_BASE}/documents/{cdc}/void/", json_body={"reason": reason}, idempotency_key=idempotency_key
        )

    def debit_note_preview(
        self, cdc: str, items: List[Dict[str, Any]], *, motivo: Optional[int] = None
    ) -> Any:
        """Calcula la nota de débito sin emitirla -- `POST /bill/sifen/documents/{cdc}/debit-note/preview/`."""
        body = {"items": items, **_compact(motivo=motivo)}
        return self._client.post(f"{_BASE}/documents/{cdc}/debit-note/preview/", json_body=body)

    def debit_note(
        self,
        cdc: str,
        items: List[Dict[str, Any]],
        *,
        motivo: Optional[int] = None,
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Emite una nota de débito electrónica (NDE) -- `POST /bill/sifen/documents/{cdc}/debit-note/`.

        `cdc` es el de la factura (FE) aprobada. Cada ítem: `descripcion`,
        `importe` (BRUTO, IVA incluido, guaraníes enteros), `tasa_iva` (10, 5 o 0
        exento) y opcional `cantidad`. `motivo` es el iMotEmi (1 a 8, default 8
        ajuste de precio; ver `catalogs("note_motives")`).
        """
        body = {"items": items, **_compact(motivo=motivo, reason=reason)}
        return self._client.post(
            f"{_BASE}/documents/{cdc}/debit-note/", json_body=body, idempotency_key=idempotency_key
        )

    def inutilizar(
        self,
        *,
        tipo_de: int,
        establecimiento: str,
        punto_expedicion: str,
        desde: int,
        hasta: int,
        reason: str,
        serie: Optional[str] = None,
        timbrado: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Inutiliza un rango (hasta 1000) de números nunca usados -- `POST /bill/sifen/inutilizaciones/`."""
        body = {
            "tipo_de": tipo_de,
            "establecimiento": establecimiento,
            "punto_expedicion": punto_expedicion,
            "desde": desde,
            "hasta": hasta,
            "reason": reason,
            **_compact(serie=serie, timbrado=timbrado),
        }
        return self._client.post(f"{_BASE}/inutilizaciones/", json_body=body, idempotency_key=idempotency_key)

    # -- KuDE y compartir -----------------------------------------------

    def kude(self, cdc: str) -> Any:
        """View-model del KuDE de un documento -- `GET /sales/sifen/documents/{cdc}/kude/`."""
        return self._client.get(f"/sales/sifen/documents/{cdc}/kude/")

    def sale_kude(self, sale_id: str) -> Any:
        """KuDE de la factura vigente de una venta -- `GET /sales/{sale_id}/sifen/kude/`."""
        return self._client.get(f"/sales/{sale_id}/sifen/kude/")

    def send_email(self, cdc: str, email: Optional[str] = None) -> Any:
        """Envía el link del KuDE por email -- `POST /bill/sifen/documents/{cdc}/send-email/`.

        `email` por defecto es el del cliente de la venta. Límite: 20 cada 5 minutos.
        """
        return self._client.post(f"{_BASE}/documents/{cdc}/send-email/", json_body=_compact(email=email))

    def public_link(self, cdc: str, expires_in_seconds: Optional[int] = None) -> Any:
        """Crea un link público (sin login) del KuDE -- `POST /bill/sifen/documents/{cdc}/public-link/`.

        Vence entre 60 segundos y 30 días (default 7 días).
        """
        return self._client.post(
            f"{_BASE}/documents/{cdc}/public-link/", json_body=_compact(expires_in_seconds=expires_in_seconds)
        )

    # -- ventas: emisión y notas de crédito -----------------------------

    def generate_invoice(self, sale_id: str) -> Any:
        """Emite la factura de una venta ya creada -- `POST /sales/generate_invoice/{sale_id}/`.

        Es asíncrona, igual que `sales.create(request_fiscal_document=True)`.
        """
        return self._client.post(f"/sales/generate_invoice/{sale_id}/", json_body={})

    def credit_note(
        self,
        sale_id: str,
        reason: str,
        *,
        lineas: List[Dict[str, Any]],
        restore_stock: Optional[bool] = None,
        update_current_account: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Emite una nota de crédito electrónica (NCE) sobre una venta -- `POST /sales/{sale_id}/credit_note/`.

        En SIFEN `lineas` es obligatorio: `[{"linea": 0, "cantidad": 1}]` con el
        índice (desde 0) del renglón de la factura. Un renglón no se acredita dos
        veces y la factura debe estar aprobada.
        """
        body = {
            "reason": reason,
            "lineas": lineas,
            **_compact(restore_stock=restore_stock, update_current_account=update_current_account),
        }
        return self._client.post(f"/sales/{sale_id}/credit_note/", json_body=body, idempotency_key=idempotency_key)

    def credit_note_preview(
        self, sale_id: str, lineas: List[Dict[str, Any]], *, reason: Optional[str] = None
    ) -> Any:
        """Calcula la nota de crédito sin emitirla -- `POST /sales/{sale_id}/credit_note/preview/`."""
        body = {"lineas": lineas, **_compact(reason=reason)}
        return self._client.post(f"/sales/{sale_id}/credit_note/preview/", json_body=body)

    # -- receptor -------------------------------------------------------

    def receptor_event(self, kind: str, cdc: str, **fields: Any) -> Any:
        """Registra un evento del receptor sobre un DE recibido -- `POST /received_invoices/sifen/events/`.

        `kind`: `notificacion`, `conformidad`, `disconformidad` o
        `desconocimiento`. `fields` admite `reason`, `total`, `emitted_at`,
        `received_at`, `total_gs` y `correction_of`.
        """
        return self._client.post("/received_invoices/sifen/events/", json_body={"kind": kind, "cdc": cdc, **fields})

    # -- configuración y diagnóstico ------------------------------------

    def readiness(self) -> Any:
        """¿Puedo emitir ahora? `can_invoice` + `blockers` + `warnings` -- `GET /bill/sifen/readiness/`."""
        return self._client.get(f"{_BASE}/readiness/")

    def set_environment(self, environment: str) -> Any:
        """Cambia el ambiente (`"test"` o `"prod"`) -- `POST /bill/sifen/environment/`.

        Se rechaza con `ConflictError` si el ambiente destino no tiene
        certificado y CSC válidos (`error_code`: `certificate_missing`, `csc_missing`, ...).
        """
        return self._client.post(f"{_BASE}/environment/", json_body={"environment": environment})

    def certificates(self, environment: Optional[str] = None) -> Any:
        """Estado (solo metadatos) del certificado y CSC -- `GET /bill/tax_info/taxpayer/sifen/certificates/[{env}/]`."""
        suffix = f"{environment}/" if environment else ""
        return self._client.get(f"/bill/tax_info/taxpayer/sifen/certificates/{suffix}")

    def ruc(self, ruc: str) -> Any:
        """Consulta un RUC en SIFEN (siConsRUC) -- `GET /bill/sifen/ruc/{ruc}/`.

        Acepta `"80069563"` o `"80069563-1"`. Un DV errado se rechaza localmente.
        Consultar el propio RUC sirve de prueba de certificado y conectividad.
        """
        return self._client.get(f"{_BASE}/ruc/{ruc}/")

    def numbering(
        self,
        *,
        tipo_de: Optional[int] = None,
        timbrado: Optional[str] = None,
        est: Optional[str] = None,
        pun_exp: Optional[str] = None,
    ) -> Any:
        """Último y próximo número de una secuencia -- `GET /bill/sifen/numbering/`."""
        params = {"tipo_de": tipo_de, "timbrado": timbrado, "est": est, "punExp": pun_exp}
        return self._client.get(f"{_BASE}/numbering/", params=params)

    def seed_numbering(
        self,
        last_used: int,
        *,
        tipo_de: Optional[int] = None,
        timbrado: Optional[str] = None,
        est: Optional[str] = None,
        pun_exp: Optional[str] = None,
        dry_run: Optional[bool] = None,
    ) -> Any:
        """Continúa la numeración desde `last_used` (solo hacia arriba) -- `POST /bill/sifen/numbering/seed/`."""
        body = {
            "last_used": last_used,
            **_compact(tipo_de=tipo_de, timbrado=timbrado, est=est, punExp=pun_exp, dry_run=dry_run),
        }
        return self._client.post(f"{_BASE}/numbering/seed/", json_body=body)

    def diagnose(self) -> Any:
        """Prueba en vivo de conectividad con el certificado propio -- `POST /bill/sifen/diagnose/`.

        Handshake mTLS + consulta del RUC del emisor; responde `ok`, la latencia de
        cada paso y `actions` (qué corregir). Un fallo es un resultado (200), no un
        error. Límite: 10 por minuto. Un token `yf_test_*` usa sifen-test.
        """
        return self._client.post(f"{_BASE}/diagnose/", json_body={})

    def verify_caja(
        self,
        *,
        establecimiento: Optional[str] = None,
        punto_expedicion: Optional[str] = None,
        sales_point_id: Optional[str] = None,
        tipo_de: Optional[int] = None,
        check_ruc: Optional[bool] = None,
    ) -> Any:
        """¿Esta caja puede emitir ahora? -- `POST /bill/sifen/verify-caja/`.

        Valida timbrado vigente, el par establecimiento/punto de expedición, que el
        RUC del certificado sea el del contribuyente y (salvo `check_ruc=False`) el
        estado del RUC emisor en SIFEN. `valid` + `checks[]` (cada uno con
        `severity` y `action`) + `actions`.
        """
        body = _compact(
            establecimiento=establecimiento,
            punto_expedicion=punto_expedicion,
            sales_point_id=sales_point_id,
            tipo_de=tipo_de,
            check_ruc=check_ruc,
        )
        return self._client.post(f"{_BASE}/verify-caja/", json_body=body)

    def lote(self, protocol: str) -> Any:
        """Consulta en vivo un lote enviado (siConsLoteDE) -- `GET /bill/sifen/lotes/{protocol}/`.

        Solo lectura: `state` (`in_process`, `concluded`...) y el resultado de cada
        documento. 404 si el protocolo no es de este tenant. Límite: 30 por minuto.
        """
        return self._client.get(f"{_BASE}/lotes/{protocol}/")

    def types(self) -> Any:
        """Tipos de documento (iTiDE) y cuáles emite la API, con su ruta -- `GET /bill/sifen/types/`."""
        return self._client.get(f"{_BASE}/types/")

    def validate_type(self, tipo_de: int, context: Optional[str] = None) -> Any:
        """¿Se puede emitir `tipo_de`? -- `POST /bill/sifen/validate-type/`.

        `context` opcional: `sale`, `standalone`, `credit_note` o `debit_note`.
        Responde `valid`, `issuable` y el `reason` cuando no.
        """
        return self._client.post(f"{_BASE}/validate-type/", json_body={"tipo_de": tipo_de, **_compact(context=context)})

    def catalogs(self, name: Optional[str] = None) -> Any:
        """Catálogos de códigos (iTiDE, iMotEmi, IVA, pagos...) -- `GET /bill/sifen/catalogs/[{name}/]`."""
        return self._client.get(f"{_BASE}/catalogs/{name}/" if name else f"{_BASE}/catalogs/")
