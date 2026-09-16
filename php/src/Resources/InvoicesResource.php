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
     * `tipo_documento`, `numero_documento` e `items` son obligatorios;
     * `tipo_comprobante` (A/B/C) se infiere de la condición de IVA del
     * emisor si se omite. Con `autorizar: true` la autorización ante AFIP
     * se dispara en segundo plano: la respuesta vuelve con
     * `authorization_pending: true` y hay que releer el comprobante
     * (`get`) hasta que el campo `cae` venga cargado. Con `autorizar: false`
     * (default) el comprobante queda en borrador para autorizar después
     * con `authorize()`. `$idempotencyKey` es opcional: evita duplicar el
     * comprobante si necesitás reintentar tras un timeout de red.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function create(array $fields, ?string $idempotencyKey = null)
    {
        return $this->client->post(self::BASE . '/invoice/', $fields, $idempotencyKey);
    }

    /**
     * Emite una factura a un cliente ya registrado. Usa el mismo endpoint
     * que `create()`, pero resuelve los datos fiscales del receptor a
     * partir de `$customerId` en vez de mandarlos sueltos.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function createForCustomer(string $customerId, array $fields = [], ?string $idempotencyKey = null)
    {
        return $this->create(array_merge(['customer_id' => $customerId], $fields), $idempotencyKey);
    }

    /**
     * Emite una nota de crédito -- `POST /bill/receipts/credit-note/`.
     * `$comprobanteAsociadoId` (el `id` del comprobante original, que debe
     * estar aprobado) e `$items` son obligatorios.
     *
     * @param array<int, array<string, mixed>> $items
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function creditNote(string $comprobanteAsociadoId, array $items, array $fields = [])
    {
        $body = array_merge(
            ['comprobante_asociado_id' => $comprobanteAsociadoId, 'items' => $items],
            $fields
        );

        return $this->client->post(self::BASE . '/credit-note/', $body);
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
