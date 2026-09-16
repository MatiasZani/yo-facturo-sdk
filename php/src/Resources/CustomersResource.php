<?php

declare(strict_types=1);

namespace YoFacturo\Resources;

use YoFacturo\Client;

/** Clientes -- `/customers`. Scope: `customers:read` / `customers:write`. */
class CustomersResource extends CrudResource
{
    public function __construct(Client $client)
    {
        parent::__construct($client, '/customers');
    }
}
