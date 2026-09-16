<?php

declare(strict_types=1);

namespace YoFacturo\Resources;

use YoFacturo\Client;

/** Ventas -- `/sales`. Scope: `sales:read` / `sales:write`. */
class SalesResource extends CrudResource
{
    public function __construct(Client $client)
    {
        parent::__construct($client, '/sales');
    }
}
