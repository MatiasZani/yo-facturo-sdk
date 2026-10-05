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

// Devolución por renglón: 'linea' es el índice (desde 0) del renglón del comprobante original.
// Alternativas: 'importe_a_acreditar' => 5000.00 o 'porcentaje_aplicar' => 50; sin ninguna anula el 100%.
$nota = $client->invoices->creditNote(
    $comprobanteId,
    null,
    ['lineas' => [['linea' => 0, 'cantidad' => 1]], 'motivo' => 'Devolución parcial de mercadería', 'autorizar' => true]
);

echo "Nota de crédito creada: {$nota['data']['id']} (estado: {$nota['data']['estado']})\n";
