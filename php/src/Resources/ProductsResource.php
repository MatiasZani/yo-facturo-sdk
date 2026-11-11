<?php

declare(strict_types=1);

namespace YoFacturo\Resources;

use YoFacturo\Client;

/** Productos -- `/products`. Scope: `products:read` / `products:write`. */
class ProductsResource extends CrudResource
{
    public function __construct(Client $client)
    {
        parent::__construct($client, '/products');
    }

    /**
     * Lista paginada -- `GET /products/list/`.
     *
     * Manda `currency_aware=1` por defecto: sin ese parametro la API omite los productos
     * cuyo `price_currency` no es la moneda por defecto de la cuenta. Cada producto en otra
     * moneda trae `price_currency`: mostrala y mandala como `currency` al vender. Pasa
     * `['currency_aware' => false]` para recibir solo los de la moneda por defecto.
     *
     * @param array<string, mixed> $params
     * @return mixed
     */
    public function list(array $params = [])
    {
        $aware = $params['currency_aware'] ?? true;
        unset($params['currency_aware']);
        if ($aware) {
            $params['currency_aware'] = 1;
        }

        return parent::list($params);
    }
}
