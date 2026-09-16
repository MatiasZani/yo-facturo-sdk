// Emite una nota de crédito asociada a un comprobante ya aprobado.
//
// Requiere: npm install yofacturo
// Uso: YOFACTURO_API_KEY=yf_live_... node nota-de-credito.js <comprobante_id>

const { YoFacturo } = require("yofacturo");

async function main() {
  const comprobanteId = process.argv[2] || process.env.COMPROBANTE_ID;
  if (!comprobanteId) {
    console.error("Uso: node nota-de-credito.js <comprobante_id>");
    process.exitCode = 1;
    return;
  }

  const client = new YoFacturo(process.env.YOFACTURO_API_KEY);

  const nota = await client.invoices.creditNote(
    comprobanteId,
    [{ descripcion: "Devolución parcial de mercadería", cantidad: 1, precio_unitario: 5000.0 }],
    { motivo: "Devolución parcial de mercadería", autorizar: true }
  );

  console.log(`Nota de crédito creada: ${nota.data.id} (estado: ${nota.data.estado})`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
