"""Lista los comprobantes aprobados, recorriendo todas las páginas.

Requiere: pip install yofacturo
Uso: YOFACTURO_API_KEY=yf_live_... python listar-comprobantes.py
"""

import os

from yofacturo import YoFacturo

client = YoFacturo(api_key=os.environ["YOFACTURO_API_KEY"])

page = 1
data = None
while True:
    respuesta = client.invoices.list(page=page, per_page=20, estado="aprobado")
    data = respuesta["data"]
    for comprobante in data["items"]:
        print(comprobante.get("id"), comprobante.get("numero_comprobante"), comprobante.get("importe_total"))
    if not data.get("has_next"):
        break
    page += 1

print(f"Total: {data['total']} comprobantes aprobados")
