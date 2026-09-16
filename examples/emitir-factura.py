"""Emite una factura electrónica (Factura C a Consumidor Final) y espera el CAE.

Requiere: pip install yofacturo
Uso: YOFACTURO_API_KEY=yf_live_... python emitir-factura.py
"""

import os
import time

from yofacturo import YoFacturo

client = YoFacturo(api_key=os.environ["YOFACTURO_API_KEY"])

factura = client.invoices.create(
    tipo_documento=99,  # Consumidor Final
    numero_documento="0",
    razon_social="CONSUMIDOR FINAL",
    items=[
        {"descripcion": "Servicio de consultoría", "cantidad": 1, "precio_unitario": 15000.00},
    ],
    importe_total=15000.00,
    autorizar=True,  # dispara la autorización ante AFIP en segundo plano
)

comprobante_id = factura["data"]["id"]
print(f"Comprobante creado: {comprobante_id} (estado: {factura['data']['estado']})")

# La autorización con AFIP corre en segundo plano: hay que releer el
# comprobante hasta que el campo `cae` venga cargado (ver /dev/invoices/).
for _ in range(10):
    comprobante = client.invoices.get(comprobante_id)["data"]
    if comprobante.get("cae"):
        print(f"CAE: {comprobante['cae']} (vence {comprobante['cae_vencimiento']})")
        break
    if comprobante["estado"] in ("error", "rechazado"):
        print(f"AFIP rechazó el comprobante: {comprobante}")
        break
    time.sleep(2)
else:
    print("Todavía no llegó el CAE -- seguí consultando GET /bill/receipts/{id}/")
