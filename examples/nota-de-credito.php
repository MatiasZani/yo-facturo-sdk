<?php

/**
 * Emite una nota de crédito asociada a un comprobante ya aprobado.
 *
 * Requiere: composer require yofacturo/yofacturo-php
 * Uso: YOFACTURO_API_KEY=yf_live_... php nota-de-credito.php <comprobante_id>
 */

require __DIR__ . '/../php/vendor/autoload.php';

use YoFacturo\Client;

$comprobanteId = $argv[1] ?? getenv('COMPROBANTE_ID');
if (!$comprobanteId) {
    fwrite(STDERR, "Uso: php nota-de-credito.php <comprobante_id>\n");
    exit(1);
}

$client = new Client((string) getenv('YOFACTURO_API_KEY'));

$nota = $client->invoices->creditNote(
    $comprobanteId,
    [['descripcion' => 'Devolución parcial de mercadería', 'cantidad' => 1, 'precio_unitario' => 5000.00]],
    ['motivo' => 'Devolución parcial de mercadería', 'autorizar' => true]
);

echo "Nota de crédito creada: {$nota['data']['id']} (estado: {$nota['data']['estado']})\n";
