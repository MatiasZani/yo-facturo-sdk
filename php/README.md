# yofacturo/yofacturo-php

SDK oficial de PHP para la [API de YoFacturo](https://yo-facturo.com/dev/) — facturación electrónica ARCA/AFIP para Argentina, catálogo, ventas y clientes, de forma programática.

Sin dependencias (usa curl nativo de PHP). PSR-4. PHP >= 7.4 con `ext-curl` y `ext-json`.

## Instalación

```bash
composer require yofacturo/yofacturo-php
```

## Uso

```php
<?php

require 'vendor/autoload.php';

use YoFacturo\Client;

$client = new Client('yf_live_...'); // Configuración → Integraciones → API Tokens

// Emitir una factura (autorizar: true dispara el CAE en segundo plano)
$factura = $client->invoices->create([
    'punto_venta' => 1,
    'tipo_documento' => 99,
    'numero_documento' => '0',
    'razon_social' => 'CONSUMIDOR FINAL',
    'items' => [
        ['descripcion' => 'Servicio de consultoría', 'cantidad' => 1, 'precio_unitario' => 15000],
    ],
    'autorizar' => true,
]);
echo $factura['data']['id'];

// Listar comprobantes
$comprobantes = $client->invoices->list(['page' => 1, 'per_page' => 20, 'estado' => 'aprobado']);

// Emitir una nota de crédito asociada
$nota = $client->invoices->creditNote(
    $factura['data']['id'],
    null,
    ['lineas' => [['linea' => 0, 'cantidad' => 1]], 'motivo' => 'Devolución parcial de mercadería'] // o importe_a_acreditar / porcentaje_aplicar
);
```

## Recursos

- `$client->invoices` — comprobantes AFIP/ARCA: `create`, `createForCustomer`, `creditNote`, `debitNote`, `list`, `get`, `authorize`, `cancel`, `supportedTypes`.
- `$client->customers` — `list`, `get`, `create`, `update`, `delete`.
- `$client->products` — `list`, `get`, `create`, `update`, `delete`. `list` envía `currency_aware=1` por defecto (productos con `price_currency` en otra moneda, ej. USD; `['currency_aware' => false]` lo desactiva); al vender esos productos mandá `currency` en `sales->create`.
- `$client->sales` — `list`, `get`, `create`, `update`, `delete`.
- `$client->services`, `$client->rentals` — `list`, `get`, `create`, `update`, `delete` (scopes `services:*` / `rentals:*`). `list` envía `currency_aware=1` por defecto, igual que `products` (`['currency_aware' => false]` lo desactiva).
- `$client->appointments`, `$client->subscriptionPlans` — `list`, `get`, `create`, `update`, `delete` (scopes `appointments:*` / `recurring:*`).

## Manejo de errores

```php
use YoFacturo\Exceptions\ValidationException;
use YoFacturo\Exceptions\RateLimitException;

try {
    $client->invoices->authorize($comprobanteId);
} catch (ValidationException $e) {
    echo $e->getApiCode(), print_r($e->getErrors(), true);
} catch (RateLimitException $e) {
    echo 'esperar ', $e->getRetryAfter(), ' segundos';
}
```

Jerarquía: `YoFacturoException` (base) → `ApiException` (con `getStatusCode()`, `getApiCode()`, `getErrors()`, `getResponseBody()`) → `AuthenticationException` (401), `ScopeException`/`PermissionException` (403, alias real vía `class_alias`), `NotFoundException` (404), `ValidationException` (400/422), `ConflictException` (409), `RateLimitException` (429, con `getRetryAfter()`), `ServerException` (5xx).

El cliente reintenta automáticamente (backoff exponencial, hasta 3 veces por defecto) ante `429` y `5xx`. Configurable con el cuarto argumento del constructor: `new Client($apiKey, Client::DEFAULT_BASE_URL, 30.0, $maxRetries)`.

## Verificación

Sin dependencias de test: si tenés `php` en el PATH, `php -l` alcanza para chequear la sintaxis de cada archivo.

```bash
find src -name "*.php" -exec php -l {} \;
```

## Links

- Documentación: https://yo-facturo.com/dev/
- Spec OpenAPI: https://api.yo-facturo.com/api/v1/openapi.json
- Estado del servicio: https://status.yo-facturo.com
