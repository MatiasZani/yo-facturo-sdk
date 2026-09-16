"""Emite una nota de crédito asociada a un comprobante ya aprobado.

Requiere: pip install yofacturo
Uso: YOFACTURO_API_KEY=yf_live_... python nota-de-credito.py <comprobante_id>
"""

import os
import sys

from yofacturo import YoFacturo

client = YoFacturo(api_key=os.environ["YOFACTURO_API_KEY"])

comprobante_id = sys.argv[1] if len(sys.argv) > 1 else os.environ["COMPROBANTE_ID"]

nota = client.invoices.credit_note(
    comprobante_id,
    items=[
        {"descripcion": "Devolución parcial de mercadería", "cantidad": 1, "precio_unitario": 5000.00},
    ],
    motivo="Devolución parcial de mercadería",
    autorizar=True,
)

print(f"Nota de crédito creada: {nota['data']['id']} (estado: {nota['data']['estado']})")
