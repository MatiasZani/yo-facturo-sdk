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
}
