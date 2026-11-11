<?php

declare(strict_types=1);

namespace YoFacturo\Resources;

use YoFacturo\Client;

/**
 * Cuentas API partner -- `/partner`.
 *
 * Solo para cuentas con contrato partner (cualquier otra recibe 403 con
 * `error_code: "API_PARTNER_REQUIRED"`). Flujo: `createTaxpayer(...)` registra
 * el CUIT de tu usuario final, el usuario delega WSFE al CUIT de YoFacturo,
 * `verifyDelegation($id)` lo confirma y después se factura con
 * `$client->invoices->create(['taxpayer_id' => $id, ...])`.
 *
 * Scopes: `taxpayers:read` para leer, `taxpayers:write` para registrar, dar de
 * baja y verificar la delegación (solo los ve una cuenta partner).
 * Guía: https://yo-facturo.com/dev/ (sección «Cuentas API partner»).
 */
class PartnerResource
{
    private const BASE = '/partner';

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

    /**
     * Registra el CUIT de un usuario final -- `POST /partner/taxpayers/` (`taxpayers:write`).
     * `$fields`: `tax_condition`, `punto_venta`, `business_name`. El `id` devuelto es el
     * `taxpayer_id` para facturar.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function createTaxpayer(string $taxId, array $fields = [])
    {
        return $this->client->post(
            self::BASE . '/taxpayers/',
            array_merge(['tax_id' => $taxId], self::compact($fields))
        );
    }

    /**
     * Lista los CUIT activos -- `GET /partner/taxpayers/` (`taxpayers:read`).
     * Paginación por cursor: pasá `data.next_cursor` como `cursor` hasta que venga `null`.
     *
     * @return mixed
     */
    public function listTaxpayers(?int $limit = null, ?string $cursor = null, ?string $q = null)
    {
        return $this->client->get(
            self::BASE . '/taxpayers/',
            self::compact(['limit' => $limit, 'cursor' => $cursor, 'q' => $q])
        );
    }

    /**
     * Un CUIT registrado -- `GET /partner/taxpayers/{taxpayerId}/` (`taxpayers:read`).
     *
     * @return mixed
     */
    public function getTaxpayer(string $taxpayerId)
    {
        return $this->client->get(self::BASE . '/taxpayers/' . $taxpayerId . '/');
    }

    /**
     * Baja lógica de un CUIT -- `DELETE /partner/taxpayers/{taxpayerId}/` (`taxpayers:write`).
     *
     * @return mixed
     */
    public function removeTaxpayer(string $taxpayerId)
    {
        return $this->client->delete(self::BASE . '/taxpayers/' . $taxpayerId . '/');
    }

    /**
     * Verifica la delegación WSFE de un CUIT --
     * `POST /partner/taxpayers/{taxpayerId}/verify-delegation/` (`taxpayers:write`, máx. 60/min).
     * `data.delegation_verified` es `true`, `false` o `null` (ARCA no contestó: reintentá).
     *
     * @return mixed
     */
    public function verifyDelegation(string $taxpayerId)
    {
        return $this->client->post(self::BASE . '/taxpayers/' . $taxpayerId . '/verify-delegation/', []);
    }

    /**
     * CUIT activos del período y estimado en ARS -- `GET /partner/usage/` (`taxpayers:read`).
     *
     * @return mixed
     */
    public function usage()
    {
        return $this->client->get(self::BASE . '/usage/');
    }
}
