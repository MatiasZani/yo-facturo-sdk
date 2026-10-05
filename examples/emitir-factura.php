<?php

/**
 * Emite una factura electrónica (Factura C a Consumidor Final) y espera el CAE.
 *
 * Requiere: composer require yofacturo/yofacturo-php
 * Uso: YOFACTURO_API_KEY=yf_live_... php emitir-factura.php
 */

require __DIR__ . '/../php/vendor/autoload.php';

use YoFacturo\Client;

$apiKey = getenv('YOFACTURO_API_KEY');
if ($apiKey === false || $apiKey === '') {
    fwrite(STDERR, "Falta la variable de entorno YOFACTURO_API_KEY\n");
    exit(1);
}

$client = new Client($apiKey);

$factura = $client->invoices->create([
    'punto_venta' => 1, // tu punto de venta habilitado en ARCA
    'tipo_documento' => 99, // Consumidor Final
    'numero_documento' => '0',
    'razon_social' => 'CONSUMIDOR FINAL',
    'items' => [
        // precio FINAL (IVA incluido): el backend calcula neto, IVA y total
        ['descripcion' => 'Servicio de consultoría', 'cantidad' => 1, 'precio_unitario' => 15000.00],
    ],
    'autorizar' => true, // dispara la autorización ante AFIP en segundo plano
]);

$comprobanteId = $factura['data']['id'];
echo "Comprobante creado: {$comprobanteId} (estado: {$factura['data']['estado']})\n";

// La autorización con AFIP corre en segundo plano: hay que releer el
// comprobante hasta que el campo `cae` venga cargado (ver /dev/invoices/).
for ($i = 0; $i < 10; $i++) {
    $comprobante = $client->invoices->get($comprobanteId)['data'];
    if (!empty($comprobante['cae'])) {
        echo "CAE: {$comprobante['cae']} (vence {$comprobante['cae_vencimiento']})\n";
        exit(0);
    }
    if (in_array($comprobante['estado'], ['error', 'rechazado'], true)) {
        echo 'AFIP rechazó el comprobante: ' . print_r($comprobante, true) . "\n";
        exit(1);
    }
    sleep(2);
}

echo "Todavía no llegó el CAE -- seguí consultando GET /bill/receipts/{id}/\n";
