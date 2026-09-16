<?php

/**
 * Lista los comprobantes aprobados, recorriendo todas las páginas.
 *
 * Requiere: composer require yofacturo/yofacturo-php
 * Uso: YOFACTURO_API_KEY=yf_live_... php listar-comprobantes.php
 */

require __DIR__ . '/../php/vendor/autoload.php';

use YoFacturo\Client;

$client = new Client((string) getenv('YOFACTURO_API_KEY'));

$page = 1;
$data = ['has_next' => true];
while (!empty($data['has_next'])) {
    $respuesta = $client->invoices->list(['page' => $page, 'per_page' => 20, 'estado' => 'aprobado']);
    $data = $respuesta['data'];
    foreach ($data['items'] as $comprobante) {
        printf(
            "%s\t%s\t%s\n",
            $comprobante['id'] ?? '',
            $comprobante['numero_comprobante'] ?? '',
            $comprobante['importe_total'] ?? ''
        );
    }
    $page++;
}

echo "Total: {$data['total']} comprobantes aprobados\n";
