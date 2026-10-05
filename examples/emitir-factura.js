// Emite una factura electrónica (Factura C a Consumidor Final) y espera el CAE.
//
// Requiere: npm install yofacturo
// Uso: YOFACTURO_API_KEY=yf_live_... node emitir-factura.js

const { YoFacturo } = require("yofacturo");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const client = new YoFacturo(process.env.YOFACTURO_API_KEY);

  const factura = await client.invoices.create({
    punto_venta: 1, // tu punto de venta habilitado en ARCA
    tipo_documento: 99, // Consumidor Final
    numero_documento: "0",
    razon_social: "CONSUMIDOR FINAL",
    // precio FINAL (IVA incluido): el backend calcula neto, IVA y total
    items: [{ descripcion: "Servicio de consultoría", cantidad: 1, precio_unitario: 15000.0 }],
    autorizar: true, // dispara la autorización ante AFIP en segundo plano
  });

  const comprobanteId = factura.data.id;
  console.log(`Comprobante creado: ${comprobanteId} (estado: ${factura.data.estado})`);

  // La autorización con AFIP corre en segundo plano: hay que releer el
  // comprobante hasta que el campo `cae` venga cargado (ver /dev/invoices/).
  for (let i = 0; i < 10; i++) {
    const { data: comprobante } = await client.invoices.get(comprobanteId);
    if (comprobante.cae) {
      console.log(`CAE: ${comprobante.cae} (vence ${comprobante.cae_vencimiento})`);
      return;
    }
    if (comprobante.estado === "error" || comprobante.estado === "rechazado") {
      console.log("AFIP rechazó el comprobante:", comprobante);
      return;
    }
    await sleep(2000);
  }
  console.log("Todavía no llegó el CAE -- seguí consultando GET /bill/receipts/{id}/");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
