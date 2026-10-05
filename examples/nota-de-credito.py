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
    # Devolución por renglón: "linea" es el índice (desde 0) del renglón del comprobante original.
    # Alternativas: importe_a_acreditar=5000.00 o porcentaje_aplicar=50; sin ninguna anula el 100%.
    lineas=[{"linea": 0, "cantidad": 1}],
    motivo="Devolución parcial de mercadería",
    autorizar=True,
)

print(f"Nota de crédito creada: {nota['data']['id']} (estado: {nota['data']['estado']})")
