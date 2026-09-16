<?php

declare(strict_types=1);

namespace YoFacturo\Resources;

use YoFacturo\Client;

/**
 * Patrón CRUD estándar de la API (ver /dev/conventions/).
 */
abstract class CrudResource
{
    protected Client $client;
    protected string $base;

    public function __construct(Client $client, string $base)
    {
        $this->client = $client;
        $this->base = $base;
    }

    /**
     * Lista paginada -- `GET {base}/list/`.
     *
     * @param array<string, mixed> $params
     * @return mixed
     */
    public function list(array $params = [])
    {
        return $this->client->get("{$this->base}/list/", $params);
    }

    /** Un registro por su id -- `GET {base}/{id}/`. @return mixed */
    public function get(string $id)
    {
        return $this->client->get("{$this->base}/{$id}/");
    }

    /**
     * Crea un registro -- `POST {base}/`. `$idempotencyKey` es opcional.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function create(array $fields = [], ?string $idempotencyKey = null)
    {
        return $this->client->post("{$this->base}/", $fields, $idempotencyKey);
    }

    /**
     * Actualiza los campos enviados -- `PUT {base}/{id}/`. Los campos
     * omitidos se mantienen sin cambios; para borrar el valor de un campo
     * mandá `null` explícito.
     *
     * @param array<string, mixed> $fields
     * @return mixed
     */
    public function update(string $id, array $fields = [])
    {
        return $this->client->put("{$this->base}/{$id}/", $fields);
    }

    /** Elimina (baja lógica) -- `DELETE {base}/{id}/`. @return mixed */
    public function delete(string $id)
    {
        return $this->client->delete("{$this->base}/{$id}/");
    }
}
