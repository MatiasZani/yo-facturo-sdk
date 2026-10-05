<?php

declare(strict_types=1);

namespace YoFacturo\Resources;

use YoFacturo\Client;

/**
 * Comprobantes electrónicos AFIP/ARCA -- `/bill/receipts`.
 *
 * Scope requerido: `invoices:read` para leer, `invoices:write` para emitir
 * o modificar comprobantes. Guía completa: https://yo-facturo.com/dev/invoices/
 */
class InvoicesResource
{
    private const BASE = '/bill/receipts';

    private Client $client;

    public function __construct(Client $client)
    {
        $this->client = $client;
    }

    /**
     * Emite un comprobante -- `POST /bill/receipts/invoice/`.
     *
     * Obligatorios: `punto_venta`, `tipo_documento`, `numero_documento` e
     * `items`. `concepto` (1 = productos, 2 = servicios, 3 = ambos) también
     * lo exige la API: el SDK manda `concepto => 1` si no lo pasás.
     * `tipo_comprobante` (A/B/C) se infiere de la condición de IVA del emisor
     * y del receptor si se omite.
     *
     * Los `precio_unitario` de `items` son precios FINALES (IVA incluido, como
     * en el POS) y el backend calcula neto, IVA y total: no hace falta mandar
     * `importe_*` ni `iva_items`. Para mandar precios NETOS de IVA pasá
     * `precios_con_iva => false`.
     *
     * La condición de IVA del receptor se resuelve con la misma regla que el
     * POS: pasá `condicion_iva_receptor_id` (código ARCA: 1 RI, 4 Exento,
     * 5 Consumidor Final, 6 Monotributo) o, equivalentes,
     * `receptor_condicion_iva` / `condicion_iva` con el nombre. Con un CUIT
     * solo, la API consulta el padrón de ARCA; si no puede determinarla emite
     * Factura B a Consumidor Final.
     *
     * Con `autorizar => true` la autorización ante AFIP se dispara en segundo
     * plano: la respuesta vuelve con `authorization_pending: true` y hay que
     * releer el comprobante (`get`) hasta que el campo `cae` venga cargado.
     * Con `autorizar => false` (default) el comprobante queda en borrador para
     * autorizar después con `authorize()`. `$idempotencyKey` es opcional:
     * evita duplicar el comprobante si necesitás reintentar tras un timeout de
     * red.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function create(array $fields, ?string $idempotencyKey = null)
    {
        return $this->client->post(
            self::BASE . '/invoice/',
            array_merge(['concepto' => 1], $fields),
            $idempotencyKey
        );
    }

    /**
     * Emite una factura a un cliente ya registrado --
     * `POST /bill/receipts/invoice/customer/`. La API toma documento, razón
     * social y condición de IVA de la ficha del cliente (`$customerId`), así
     * que no se mandan `tipo_documento`, `numero_documento` ni la condición.
     * Obligatorios: `punto_venta` e `items` (`concepto` va en 1 si no lo
     * pasás). Los precios, `precios_con_iva` y `autorizar` funcionan igual que
     * en `create()`. A diferencia de `create()`, la respuesta trae el id del
     * comprobante en `data.factura_id` (no en `data.id`).
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function createForCustomer(string $customerId, array $fields = [], ?string $idempotencyKey = null)
    {
        return $this->client->post(
            self::BASE . '/invoice/customer/',
            array_merge(['concepto' => 1], $fields, ['customer_id' => $customerId]),
            $idempotencyKey
        );
    }

    /**
     * Emite una nota de crédito -- `POST /bill/receipts/credit-note/`.
     * `$comprobanteAsociadoId` es el `id` del comprobante original, que debe
     * estar aprobado. Cuánto acreditar se indica con UNO de estos campos de
     * `$fields`:
     *
     * - `lineas => [['linea' => 1, 'cantidad' => 1]]`: devolución por renglón.
     *   `linea` es el índice (desde 0) del renglón del comprobante original y
     *   `cantidad` cuántas unidades se devuelven. El backend calcula neto e IVA.
     * - `importe_a_acreditar => 605`: un monto (bonificación, ajuste de precio).
     * - `porcentaje_aplicar => 50`: un porcentaje del comprobante (0 a 100].
     * - Ninguno: anula el 100% del comprobante.
     *
     * `$items` ya no sirve para devoluciones parciales (pasá `null`): la API
     * calcula las líneas de la nota a partir del original y un `items` que no
     * coincida con el total de la nota se rechaza con 400.
     *
     * @param array<int, array<string, mixed>>|null $items
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function creditNote(string $comprobanteAsociadoId, ?array $items = null, array $fields = [])
    {
        $body = ['comprobante_asociado_id' => $comprobanteAsociadoId];
        if ($items !== null) {
            $body['items'] = $items;
        }

        return $this->client->post(self::BASE . '/credit-note/', array_merge($body, $fields));
    }

    /**
     * Emite una nota de débito -- `POST /bill/receipts/debit-note/`.
     *
     * @param array<int, array<string, mixed>> $items
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function debitNote(string $comprobanteAsociadoId, array $items, array $fields = [])
    {
        $body = array_merge(
            ['comprobante_asociado_id' => $comprobanteAsociadoId, 'items' => $items],
            $fields
        );

        return $this->client->post(self::BASE . '/debit-note/', $body);
    }

    /**
     * Lista comprobantes con paginación y filtros -- `GET /bill/receipts/list/`.
     *
     * @param array<string, mixed> $params
     * @return mixed
     */
    public function list(array $params = [])
    {
        return $this->client->get(self::BASE . '/list/', $params);
    }

    /** Obtiene un comprobante por su id -- `GET /bill/receipts/{id}/`. @return mixed */
    public function get(string $comprobanteId)
    {
        return $this->client->get(self::BASE . "/{$comprobanteId}/");
    }

    /**
     * Autoriza un comprobante en borrador ante AFIP (obtiene el CAE) --
     * `POST /bill/receipts/authorize/{id}/`. A diferencia de `create()` con
     * `autorizar: true`, esta llamada es síncrona: espera a AFIP y, si lo
     * aprueba, la respuesta ya trae `cae` y `cae_vencimiento`. Si AFIP lo
     * rechaza, lanza `ValidationException` con el motivo.
     *
     * @return mixed
     */
    public function authorize(string $comprobanteId)
    {
        return $this->client->post(self::BASE . "/authorize/{$comprobanteId}/", []);
    }

    /**
     * Anula un comprobante ya autorizado -- `POST /bill/receipts/cancel/{id}/`.
     * Genera automáticamente una nota de crédito por el importe total del
     * comprobante original (viene en `data.nota_credito` de la respuesta).
     *
     * @return mixed
     */
    public function cancel(string $comprobanteId, ?string $motivo = null)
    {
        $body = $motivo !== null ? ['motivo' => $motivo] : [];

        return $this->client->post(self::BASE . "/cancel/{$comprobanteId}/", $body);
    }

    /**
     * Tipos de comprobante soportados según la condición fiscal del emisor
     * -- `GET /bill/receipts/supported-types/`.
     *
     * @return mixed
     */
    public function supportedTypes()
    {
        return $this->client->get(self::BASE . '/supported-types/');
    }
}
