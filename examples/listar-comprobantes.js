// Lista los comprobantes aprobados, recorriendo todas las páginas.
//
// Requiere: npm install yofacturo
// Uso: YOFACTURO_API_KEY=yf_live_... node listar-comprobantes.js

const { YoFacturo } = require("yofacturo");

async function main() {
  const client = new YoFacturo(process.env.YOFACTURO_API_KEY);

  let page = 1;
  let data;
  do {
    const respuesta = await client.invoices.list({ page, per_page: 20, estado: "aprobado" });
    data = respuesta.data;
    for (const comprobante of data.items) {
      console.log(comprobante.id, comprobante.numero_comprobante, comprobante.importe_total);
    }
    page += 1;
  } while (data.has_next);

  console.log(`Total: ${data.total} comprobantes aprobados`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
