import assert from "node:assert/strict";
import { test } from "node:test";

import { ConflictError, ServerError, YoFacturo } from "../src";
import { createFakeTransport, type QueuedResponse } from "../test-support/fake-transport";

const CDC = "01800695631001001000000112026100710000000013";
const OK: QueuedResponse[] = [[200, {}, { success: true, data: {} }]];

function makeClient(responses: QueuedResponse[] = OK) {
  const { transport, calls } = createFakeTransport(responses);
  const client = new YoFacturo("yf_live_test_token", { transport, sleep: async () => {} });
  return { client, calls };
}

async function call(invoke: (c: YoFacturo) => Promise<unknown>) {
  const { client, calls } = makeClient();
  await invoke(client);
  return calls[0];
}

test("list() sends only the filters that were given", async () => {
  const c = await call((client) =>
    client.sifen.list({ status: "approved,approved_obs", caja: "001-002", limit: 50, cursor: undefined })
  );
  assert.equal(c.method, "GET");
  const [path, query] = c.url.split("?");
  assert.ok(path.endsWith("/bill/sifen/documents/"));
  assert.ok(query.includes("status=approved%2Capproved_obs"));
  assert.ok(query.includes("caja=001-002"));
  assert.ok(query.includes("limit=50"));
  assert.ok(!query.includes("cursor") && !query.includes("tipo_de"));
});

test("get() / events() / query() hit the CDC routes", async () => {
  assert.ok((await call((c) => c.sifen.get(CDC))).url.endsWith(`/bill/sifen/documents/${CDC}/`));
  assert.ok((await call((c) => c.sifen.events(CDC))).url.endsWith(`/bill/sifen/documents/${CDC}/events/`));
  const q = await call((c) => c.sifen.query(CDC));
  assert.equal(q.method, "POST");
  assert.ok(q.url.endsWith(`/bill/sifen/documents/${CDC}/consulta/`));
  assert.deepEqual(q.body, {});
});

test("void() sends the reason and the Idempotency-Key header", async () => {
  const c = await call((client) => client.sifen.void(CDC, "Error de carga", "void-1"));
  assert.ok(c.url.endsWith(`/bill/sifen/documents/${CDC}/void/`));
  assert.deepEqual(c.body, { reason: "Error de carga" });
  assert.equal(c.headers["Idempotency-Key"], "void-1");
  assert.equal((await call((client) => client.sifen.void(CDC, "Error de carga"))).headers["Idempotency-Key"], undefined);
});

const ITEMS = [{ descripcion: "Ajuste", importe: 11000, tasa_iva: 10 as const }];

test("debitNotePreview() and debitNote() send items, drop unset optionals and forward the key", async () => {
  const p = await call((c) => c.sifen.debitNotePreview(CDC, ITEMS, 8));
  assert.ok(p.url.endsWith(`/bill/sifen/documents/${CDC}/debit-note/preview/`));
  assert.deepEqual(p.body, { items: ITEMS, motivo: 8 });
  const d = await call((c) => c.sifen.debitNote(CDC, ITEMS, { reason: "Ajuste" }, "nde-1"));
  assert.ok(d.url.endsWith(`/bill/sifen/documents/${CDC}/debit-note/`));
  assert.deepEqual(d.body, { items: ITEMS, reason: "Ajuste" });
  assert.equal(d.headers["Idempotency-Key"], "nde-1");
});

test("inutilizar() posts the range", async () => {
  const c = await call((client) =>
    client.sifen.inutilizar({
      tipo_de: 1,
      establecimiento: "001",
      punto_expedicion: "001",
      desde: 5,
      hasta: 9,
      reason: "Talonario perdido",
    })
  );
  assert.ok(c.url.endsWith("/bill/sifen/inutilizaciones/"));
  assert.deepEqual(c.body, {
    tipo_de: 1,
    establecimiento: "001",
    punto_expedicion: "001",
    desde: 5,
    hasta: 9,
    reason: "Talonario perdido",
  });
});

test("kude, sendEmail and publicLink routes", async () => {
  assert.ok((await call((c) => c.sifen.kude(CDC))).url.endsWith(`/sales/sifen/documents/${CDC}/kude/`));
  assert.ok((await call((c) => c.sifen.saleKude("sale-1"))).url.endsWith("/sales/sale-1/sifen/kude/"));
  const mail = await call((c) => c.sifen.sendEmail(CDC));
  assert.ok(mail.url.endsWith(`/bill/sifen/documents/${CDC}/send-email/`));
  assert.deepEqual(mail.body, {});
  assert.deepEqual((await call((c) => c.sifen.sendEmail(CDC, "a@b.com"))).body, { email: "a@b.com" });
  const link = await call((c) => c.sifen.publicLink(CDC, 3600));
  assert.ok(link.url.endsWith(`/bill/sifen/documents/${CDC}/public-link/`));
  assert.deepEqual(link.body, { expires_in_seconds: 3600 });
  assert.deepEqual((await call((c) => c.sifen.publicLink(CDC))).body, {});
});

test("generateInvoice() posts to the sale route", async () => {
  const c = await call((client) => client.sifen.generateInvoice("sale-1"));
  assert.equal(c.method, "POST");
  assert.ok(c.url.endsWith("/sales/generate_invoice/sale-1/"));
});

test("creditNote() sends lineas, extras and the key; the preview sends lineas only", async () => {
  const lineas = [{ linea: 0, cantidad: 1 }];
  const c = await call((client) =>
    client.sifen.creditNote("sale-1", "Devolución", lineas, { restore_stock: true }, "nce-1")
  );
  assert.ok(c.url.endsWith("/sales/sale-1/credit_note/"));
  assert.deepEqual(c.body, { reason: "Devolución", lineas, restore_stock: true });
  assert.equal(c.headers["Idempotency-Key"], "nce-1");
  const p = await call((client) => client.sifen.creditNotePreview("sale-1", lineas));
  assert.ok(p.url.endsWith("/sales/sale-1/credit_note/preview/"));
  assert.deepEqual(p.body, { lineas });
});

test("receptorEvent() merges the extra fields", async () => {
  const c = await call((client) => client.sifen.receptorEvent("conformidad", CDC, { total: true, reason: "Ok" }));
  assert.ok(c.url.endsWith("/received_invoices/sifen/events/"));
  assert.deepEqual(c.body, { total: true, reason: "Ok", kind: "conformidad", cdc: CDC });
});

test("readiness, catalogs, ruc and certificates are plain GETs", async () => {
  assert.ok((await call((c) => c.sifen.readiness())).url.endsWith("/bill/sifen/readiness/"));
  assert.ok((await call((c) => c.sifen.catalogs())).url.endsWith("/bill/sifen/catalogs/"));
  assert.ok((await call((c) => c.sifen.catalogs("note_motives"))).url.endsWith("/bill/sifen/catalogs/note_motives/"));
  assert.ok((await call((c) => c.sifen.ruc("80069563-1"))).url.endsWith("/bill/sifen/ruc/80069563-1/"));
  assert.ok((await call((c) => c.sifen.certificates())).url.endsWith("/bill/tax_info/taxpayer/sifen/certificates/"));
  assert.ok(
    (await call((c) => c.sifen.certificates("prod"))).url.endsWith("/bill/tax_info/taxpayer/sifen/certificates/prod/")
  );
});

test("numbering() and seedNumbering() use the wire name punExp", async () => {
  const n = await call((c) => c.sifen.numbering({ tipo_de: 1, est: "001", punExp: "002" }));
  const [path, query] = n.url.split("?");
  assert.ok(path.endsWith("/bill/sifen/numbering/"));
  assert.ok(query.includes("punExp=002") && query.includes("est=001") && query.includes("tipo_de=1"));
  const s = await call((c) => c.sifen.seedNumbering(120, { punExp: "002", dry_run: true }));
  assert.ok(s.url.endsWith("/bill/sifen/numbering/seed/"));
  assert.deepEqual(s.body, { last_used: 120, punExp: "002", dry_run: true });
});

test("setEnvironment() conflict raises ConflictError", async () => {
  const { client } = makeClient([
    [409, {}, { success: false, error: "No prod certificate is uploaded", code: "CONFLICT", error_code: "certificate_missing" }],
  ]);
  await assert.rejects(client.sifen.setEnvironment("prod"), ConflictError);
});

test("query() against a down SIFEN raises ServerError after the retries", async () => {
  const down: QueuedResponse = [503, {}, { success: false, error: "SIFEN is not reachable right now", code: "SERVICE_UNAVAILABLE" }];
  const { client, calls } = makeClient([down, down, down, down]);
  await assert.rejects(client.sifen.query(CDC), ServerError);
  assert.equal(calls.length, 4);
});

test("create() posts a standalone document with the Idempotency-Key header", async () => {
  const c = await call((client) =>
    client.sifen.create(
      { items: [{ descripcion: "Servicio", importe: 11000, tasa_iva: 10 }], client_reference: "order-7", sales_point_id: undefined },
      "doc-1"
    )
  );
  assert.equal(c.method, "POST");
  assert.ok(c.url.endsWith("/bill/sifen/documents/"));
  assert.deepEqual(c.body, { tipo_de: 1, items: [{ descripcion: "Servicio", importe: 11000, tasa_iva: 10 }], client_reference: "order-7" });
  assert.equal(c.headers["Idempotency-Key"], "doc-1");
});

test("diagnose() / verifyCaja() / lote() hit the live diagnostics routes", async () => {
  const d = await call((client) => client.sifen.diagnose());
  assert.equal(d.method, "POST");
  assert.ok(d.url.endsWith("/bill/sifen/diagnose/"));
  const v = await call((client) => client.sifen.verifyCaja({ establecimiento: "001", punto_expedicion: "002", check_ruc: false }));
  assert.ok(v.url.endsWith("/bill/sifen/verify-caja/"));
  assert.deepEqual(v.body, { establecimiento: "001", punto_expedicion: "002", check_ruc: false });
  const l = await call((client) => client.sifen.lote("987654321"));
  assert.equal(l.method, "GET");
  assert.ok(l.url.endsWith("/bill/sifen/lotes/987654321/"));
});

test("types() / validateType() mirror the AFIP type routes", async () => {
  assert.ok((await call((c) => c.sifen.types())).url.endsWith("/bill/sifen/types/"));
  const v = await call((c) => c.sifen.validateType(1, "standalone"));
  assert.ok(v.url.endsWith("/bill/sifen/validate-type/"));
  assert.deepEqual(v.body, { tipo_de: 1, context: "standalone" });
  assert.deepEqual((await call((c) => c.sifen.validateType(4))).body, { tipo_de: 4 });
});
