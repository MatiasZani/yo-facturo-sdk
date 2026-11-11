<?php

declare(strict_types=1);

namespace YoFacturo\Resources;

use YoFacturo\Client;

/** Turnos -- `/appointments`. Scope: `appointments:read` / `appointments:write`. */
class AppointmentsResource extends CrudResource
{
    public function __construct(Client $client)
    {
        parent::__construct($client, '/appointments');
    }
}
