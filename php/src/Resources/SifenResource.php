<?php

declare(strict_types=1);

namespace YoFacturo\Resources;

use YoFacturo\Client;

/**
 * Facturación electrónica de Paraguay (SIFEN) -- `/bill/sifen`.
 *
 * La emisión sale por `$client->sales->create([..., 'request_fiscal_document' => true])`
 * (o `generateInvoice()` sobre una venta existente) y es asíncrona: la
 * respuesta no trae el CDC, hay que releer la venta (`$client->sales->get($id)`,
 * campo `fiscal`) o este recurso (`get($cdc)`) hasta que `status` sea
 * `approved`, o suscribirse a los webhooks `invoice.authorized` /
 * `invoice.rejected` / `invoice.cancelled` (`system: "sifen"`).
 *
 * Scope requerido: `invoices:read` para leer, `invoices:write` para operar
 * documentos, `accounting:read|write` para la configuración (certificados,
 * ambiente, numeración), `received_invoices:write` para los eventos del
 * receptor. Un token `yf_test_*` lee todo pero nunca transmite a SIFEN (409).
 * Guía completa: https://yo-facturo.com/dev/paraguay-sifen/
 *
 * Fuera del SDK: la subida del certificado PKCS#12 (`multipart/form-data`) y
 * la descarga del XML firmado (`application/xml`); usá HTTP directo, ver la guía.
 */
class SifenResource
{
    private const BASE = '/bill/sifen';

    private Client $client;

    public function __construct(Client $client)
    {
        $this->client = $client;
    }

    /**
     * @param array<string, mixed> $fields
     * @return array<string, mixed>
     */
    private static function compact(array $fields): array
    {
        return array_filter($fields, static fn ($value): bool => $value !== null);
    }

    // -- documentos ---------------------------------------------------------

    /**
     * Lista documentos SIFEN, el más nuevo primero -- `GET /bill/sifen/documents/`.
     * Filtros: `tipo_de`, `status` (varios separados por coma), `date_from`,
     * `date_to`, `sale_id`, `cdc`, `caja` (`'001-002'`), `limit`, `cursor`. La
     * paginación es por cursor: pasá `data.next_cursor` hasta que venga `null`.
     *
     * @param array<string, mixed> $params
     * @return mixed
     */
    public function list(array $params = [])
    {
        return $this->client->get(self::BASE . '/documents/', $params);
    }

    /**
     * Emite una factura electrónica (FE, `tipo_de` 1) SIN venta -- `POST /bill/sifen/documents/`.
     * `$fields`: `items` (cada uno con `descripcion`, `cantidad`, `precio_unitario` o `importe`
     * BRUTO IVA incluido en guaraníes enteros, `tasa_iva` 10/5/0; el backend calcula base, IVA y
     * total), `receptor` (`document_type` ruc|ci|none, `document_number`, `name`, `email`,
     * `phone`), `condicion`, `pago_tipo`, `plazo_dias`, caja (`sales_point_id` o
     * `establecimiento` + `punto_expedicion`), `info_emisor` y `client_reference` (repite el mismo
     * documento sin numerar otro). Es asíncrona: la respuesta trae el CDC en estado `signed`; leé
     * `get($cdc)` hasta `approved`. Solo la FE (1); las notas usan `debitNote` y `creditNote`.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function create(array $fields, ?string $idempotencyKey = null)
    {
        return $this->client->post(
            self::BASE . '/documents/',
            array_merge(['tipo_de' => 1], self::compact($fields)),
            $idempotencyKey
        );
    }

    /**
     * Obtiene un documento por su CDC (44 dígitos) -- `GET /bill/sifen/documents/{cdc}/`.
     * Trae `status`, número, timbrado, totales, QR, protocolo, `sifen_messages`
     * (cada `dCodRes`/`dMsgRes` que contestó SIFEN: el motivo de un rechazo) y
     * los eventos del documento.
     *
     * @return mixed
     */
    public function get(string $cdc)
    {
        return $this->client->get(self::BASE . '/documents/' . $cdc . '/');
    }

    /**
     * Consulta el documento en vivo a SIFEN (siConsDE) --
     * `POST /bill/sifen/documents/{cdc}/consulta/`. Actualiza el estado local
     * si SIFEN ya lo aprobó. Si SIFEN no responde lanza `ServerException`
     * (503) y el estado local no cambia. Límite: 30 por minuto.
     *
     * @return mixed
     */
    public function query(string $cdc)
    {
        return $this->client->post(self::BASE . '/documents/' . $cdc . '/consulta/', []);
    }

    /**
     * Historial de eventos de un documento -- `GET /bill/sifen/documents/{cdc}/events/`.
     *
     * @return mixed
     */
    public function events(string $cdc)
    {
        return $this->client->get(self::BASE . '/documents/' . $cdc . '/events/');
    }

    /**
     * Anula un documento -- `POST /bill/sifen/documents/{cdc}/void/`. Según el
     * estado: cancelación (FE aprobada hace menos de 48 h), nota de crédito por
     * el saldo (fuera de ventana) o inutilización (número nunca aprobado);
     * `data.action` dice cuál se hizo. `$reason`: 5 a 500 caracteres.
     *
     * @return mixed
     */
    public function void(string $cdc, string $reason, ?string $idempotencyKey = null)
    {
        return $this->client->post(
            self::BASE . '/documents/' . $cdc . '/void/',
            ['reason' => $reason],
            $idempotencyKey
        );
    }

    /**
     * Calcula la nota de débito sin emitirla --
     * `POST /bill/sifen/documents/{cdc}/debit-note/preview/`.
     *
     * @param array<int, array<string, mixed>> $items
     * @return mixed
     */
    public function debitNotePreview(string $cdc, array $items, ?int $motivo = null)
    {
        return $this->client->post(
            self::BASE . '/documents/' . $cdc . '/debit-note/preview/',
            array_merge(['items' => $items], self::compact(['motivo' => $motivo]))
        );
    }

    /**
     * Emite una nota de débito electrónica (NDE) --
     * `POST /bill/sifen/documents/{cdc}/debit-note/`. `$cdc` es el de la
     * factura (FE) aprobada. Cada ítem: `descripcion`, `importe` (BRUTO, IVA
     * incluido, guaraníes enteros), `tasa_iva` (10, 5 o 0 exento) y opcional
     * `cantidad`. `$motivo` es el iMotEmi (1 a 8, default 8 ajuste de precio;
     * ver `catalogs('note_motives')`).
     *
     * @param array<int, array<string, mixed>> $items
     * @return mixed
     */
    public function debitNote(
        string $cdc,
        array $items,
        ?int $motivo = null,
        ?string $reason = null,
        ?string $idempotencyKey = null
    ) {
        return $this->client->post(
            self::BASE . '/documents/' . $cdc . '/debit-note/',
            array_merge(['items' => $items], self::compact(['motivo' => $motivo, 'reason' => $reason])),
            $idempotencyKey
        );
    }

    /**
     * Inutiliza un rango (hasta 1000) de números nunca usados --
     * `POST /bill/sifen/inutilizaciones/`. `$fields`: `tipo_de`,
     * `establecimiento`, `punto_expedicion`, `desde`, `hasta`, `reason` y
     * opcionales `serie`, `timbrado`.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function inutilizar(array $fields, ?string $idempotencyKey = null)
    {
        return $this->client->post(self::BASE . '/inutilizaciones/', $fields, $idempotencyKey);
    }

    // -- KuDE y compartir ---------------------------------------------------

    /**
     * View-model del KuDE de un documento -- `GET /sales/sifen/documents/{cdc}/kude/`.
     *
     * @return mixed
     */
    public function kude(string $cdc)
    {
        return $this->client->get('/sales/sifen/documents/' . $cdc . '/kude/');
    }

    /**
     * KuDE de la factura vigente de una venta -- `GET /sales/{saleId}/sifen/kude/`.
     *
     * @return mixed
     */
    public function saleKude(string $saleId)
    {
        return $this->client->get('/sales/' . $saleId . '/sifen/kude/');
    }

    /**
     * Envía el link del KuDE por email -- `POST /bill/sifen/documents/{cdc}/send-email/`.
     * `$email` por defecto es el del cliente de la venta. Límite: 20 cada 5 minutos.
     *
     * @return mixed
     */
    public function sendEmail(string $cdc, ?string $email = null)
    {
        return $this->client->post(
            self::BASE . '/documents/' . $cdc . '/send-email/',
            self::compact(['email' => $email])
        );
    }

    /**
     * Crea un link público (sin login) del KuDE --
     * `POST /bill/sifen/documents/{cdc}/public-link/`. Vence entre 60 segundos
     * y 30 días (default 7 días).
     *
     * @return mixed
     */
    public function publicLink(string $cdc, ?int $expiresInSeconds = null)
    {
        return $this->client->post(
            self::BASE . '/documents/' . $cdc . '/public-link/',
            self::compact(['expires_in_seconds' => $expiresInSeconds])
        );
    }

    // -- ventas: emisión y notas de crédito ---------------------------------

    /**
     * Emite la factura de una venta ya creada -- `POST /sales/generate_invoice/{saleId}/`.
     * Es asíncrona, igual que `sales->create(['request_fiscal_document' => true])`.
     *
     * @return mixed
     */
    public function generateInvoice(string $saleId)
    {
        return $this->client->post('/sales/generate_invoice/' . $saleId . '/', []);
    }

    /**
     * Emite una nota de crédito electrónica (NCE) sobre una venta --
     * `POST /sales/{saleId}/credit_note/`. En SIFEN `$lineas` es obligatorio:
     * `[['linea' => 0, 'cantidad' => 1]]` con el índice (desde 0) del renglón de
     * la factura. Un renglón no se acredita dos veces y la factura debe estar
     * aprobada. `$fields` admite `restore_stock` y `update_current_account`.
     *
     * @param array<int, array<string, mixed>> $lineas
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function creditNote(
        string $saleId,
        string $reason,
        array $lineas,
        array $fields = [],
        ?string $idempotencyKey = null
    ) {
        return $this->client->post(
            '/sales/' . $saleId . '/credit_note/',
            array_merge(['reason' => $reason, 'lineas' => $lineas], self::compact($fields)),
            $idempotencyKey
        );
    }

    /**
     * Calcula la nota de crédito sin emitirla -- `POST /sales/{saleId}/credit_note/preview/`.
     *
     * @param array<int, array<string, mixed>> $lineas
     * @return mixed
     */
    public function creditNotePreview(string $saleId, array $lineas, ?string $reason = null)
    {
        return $this->client->post(
            '/sales/' . $saleId . '/credit_note/preview/',
            array_merge(['lineas' => $lineas], self::compact(['reason' => $reason]))
        );
    }

    // -- receptor -----------------------------------------------------------

    /**
     * Registra un evento del receptor sobre un DE recibido --
     * `POST /received_invoices/sifen/events/`. `$kind`: `notificacion`,
     * `conformidad`, `disconformidad` o `desconocimiento`. `$fields` admite
     * `reason`, `total`, `emitted_at`, `received_at`, `total_gs` y `correction_of`.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function receptorEvent(string $kind, string $cdc, array $fields = [])
    {
        return $this->client->post(
            '/received_invoices/sifen/events/',
            array_merge($fields, ['kind' => $kind, 'cdc' => $cdc])
        );
    }

    // -- configuración y diagnóstico ----------------------------------------

    /**
     * ¿Puedo emitir ahora? `can_invoice` + `blockers` + `warnings` -- `GET /bill/sifen/readiness/`.
     *
     * @return mixed
     */
    public function readiness()
    {
        return $this->client->get(self::BASE . '/readiness/');
    }

    /**
     * Cambia el ambiente (`'test'` o `'prod'`) -- `POST /bill/sifen/environment/`.
     * Se rechaza con `ConflictException` si el ambiente destino no tiene
     * certificado y CSC válidos (`error_code`: `certificate_missing`,
     * `csc_missing`, ...).
     *
     * @return mixed
     */
    public function setEnvironment(string $environment)
    {
        return $this->client->post(self::BASE . '/environment/', ['environment' => $environment]);
    }

    /**
     * Estado (solo metadatos) del certificado y CSC --
     * `GET /bill/tax_info/taxpayer/sifen/certificates/[{env}/]`.
     *
     * @return mixed
     */
    public function certificates(?string $environment = null)
    {
        $suffix = $environment !== null ? $environment . '/' : '';

        return $this->client->get('/bill/tax_info/taxpayer/sifen/certificates/' . $suffix);
    }

    /**
     * Consulta un RUC en SIFEN (siConsRUC) -- `GET /bill/sifen/ruc/{ruc}/`.
     * Acepta `'80069563'` o `'80069563-1'`. Un DV errado se rechaza localmente.
     * Consultar el propio RUC sirve de prueba de certificado y conectividad.
     *
     * @return mixed
     */
    public function ruc(string $ruc)
    {
        return $this->client->get(self::BASE . '/ruc/' . $ruc . '/');
    }

    /**
     * Prueba en vivo de conectividad con el certificado propio -- `POST /bill/sifen/diagnose/`.
     * Handshake mTLS + consulta del RUC emisor: `ok`, latencia de cada paso y `actions`. Un fallo
     * es un resultado (200), no un error. Límite: 10 por minuto.
     *
     * @return mixed
     */
    public function diagnose()
    {
        return $this->client->post(self::BASE . '/diagnose/', []);
    }

    /**
     * ¿Esta caja puede emitir ahora? -- `POST /bill/sifen/verify-caja/`. `$fields`:
     * `establecimiento`, `punto_expedicion` | `sales_point_id`, `tipo_de`, `check_ruc` (`false`
     * omite la consulta del RUC emisor). Responde `valid`, `checks[]` (con `severity` y
     * `action`) y `actions`.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function verifyCaja(array $fields = [])
    {
        return $this->client->post(self::BASE . '/verify-caja/', self::compact($fields));
    }

    /**
     * Consulta en vivo un lote enviado (siConsLoteDE) -- `GET /bill/sifen/lotes/{protocol}/`.
     * Solo lectura; 404 si el protocolo no es de este tenant. Límite: 30 por minuto.
     *
     * @return mixed
     */
    public function lote(string $protocol)
    {
        return $this->client->get(self::BASE . '/lotes/' . $protocol . '/');
    }

    /**
     * Tipos de documento (iTiDE) y cuáles emite la API, con su ruta -- `GET /bill/sifen/types/`.
     *
     * @return mixed
     */
    public function types()
    {
        return $this->client->get(self::BASE . '/types/');
    }

    /**
     * ¿Se puede emitir `$tipoDe`? -- `POST /bill/sifen/validate-type/`. `$context` opcional:
     * `sale`, `standalone`, `credit_note` o `debit_note`. Responde `valid`, `issuable` y `reason`.
     *
     * @return mixed
     */
    public function validateType(int $tipoDe, ?string $context = null)
    {
        return $this->client->post(
            self::BASE . '/validate-type/',
            array_merge(['tipo_de' => $tipoDe], self::compact(['context' => $context]))
        );
    }

    /**
     * Último y próximo número de una secuencia -- `GET /bill/sifen/numbering/`.
     * `$params`: `tipo_de`, `timbrado`, `est`, `punExp`.
     *
     * @param array<string, mixed> $params
     * @return mixed
     */
    public function numbering(array $params = [])
    {
        return $this->client->get(self::BASE . '/numbering/', $params);
    }

    /**
     * Continúa la numeración desde `$lastUsed` (solo hacia arriba) --
     * `POST /bill/sifen/numbering/seed/`. `$fields`: `tipo_de`, `timbrado`,
     * `est`, `punExp`, `dry_run`.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function seedNumbering(int $lastUsed, array $fields = [])
    {
        return $this->client->post(
            self::BASE . '/numbering/seed/',
            array_merge(['last_used' => $lastUsed], self::compact($fields))
        );
    }

    /**
     * Catálogos de códigos (iTiDE, iMotEmi, IVA, pagos...) -- `GET /bill/sifen/catalogs/[{name}/]`.
     *
     * @return mixed
     */
    public function catalogs(?string $name = null)
    {
        return $this->client->get(self::BASE . ($name !== null ? '/catalogs/' . $name . '/' : '/catalogs/'));
    }
}
