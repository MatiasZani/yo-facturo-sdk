import assert from "node:assert/strict";
import { test } from "node:test";

import { YoFacturo } from "../src";
import { createFakeTransport, type QueuedResponse } from "../test-support/fake-transport";

function makeClient(responses: QueuedResponse[]) {
  const { transport, calls } = createFakeTransport(responses);
  const client = new YoFacturo("yf_live_test_token", { transport, sleep: async () => {} });
  return { client, calls };
}

test("create() posts the expected body", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { id: "abc" } }]]);
  await client.invoices.create({
    tipo_documento: 99,
    numero_documento: "0",
    razon_social: "CONSUMIDOR FINAL",
    items: [{ descripcion: "Servicio", cantidad: 1, precio_unitario: 1000 }],
    autorizar: true,
  });
  const call = calls[0];
  assert.equal(call.method, "POST");
  assert.ok(call.url.endsWith("/bill/receipts/invoice/"));
  assert.equal((call.body as any).numero_documento, "0");
  assert.equal((call.body as any).autorizar, true);
});

test("create() sends the Idempotency-Key header when given", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { id: "abc" } }]]);
  await client.invoices.create(
    { tipo_documento: 99, numero_documento: "0", items: [] },
    "factura-2026-05-21-001"
  );
  assert.equal(calls[0].headers["Idempotency-Key"], "factura-2026-05-21-001");
});

test("createForCustomer() sets customer_id", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { id: "abc" } }]]);
  await client.invoices.createForCustomer("cust_123", {
    items: [{ descripcion: "Servicio", cantidad: 1, precio_unitario: 1000 }],
    autorizar: false,
  });
  const call = calls[0];
  assert.ok(call.url.endsWith("/bill/receipts/invoice/"));
  assert.equal((call.body as any).customer_id, "cust_123");
  assert.equal((call.body as any).autorizar, false);
});

test("creditNote() requires comprobanteAsociadoId", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { id: "nc_1" } }]]);
  await client.invoices.creditNote(
    "factura_original_id",
    [{ descripcion: "Devolución", cantidad: 1, precio_unitario: 100 }],
    { motivo: "Devolución parcial" }
  );
  const call = calls[0];
  assert.ok(call.url.endsWith("/bill/receipts/credit-note/"));
  assert.equal((call.body as any).comprobante_asociado_id, "factura_original_id");
  assert.equal((call.body as any).motivo, "Devolución parcial");
});

test("debitNote() hits the debit-note endpoint", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { id: "nd_1" } }]]);
  await client.invoices.debitNote("factura_original_id", [
    { descripcion: "Interés", cantidad: 1, precio_unitario: 50 },
  ]);
  assert.ok(calls[0].url.endsWith("/bill/receipts/debit-note/"));
});

test("list() forwards filters as query params", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { items: [] } }]]);
  await client.invoices.list({ page: 1, per_page: 20, estado: "aprobado", tipo_comprobante: 6 });
  const call = calls[0];
  assert.equal(call.method, "GET");
  assert.ok(call.url.includes("/bill/receipts/list/"));
  assert.ok(call.url.includes("estado=aprobado"));
  assert.ok(call.url.includes("tipo_comprobante=6"));
});

test("get() fetches by id", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { id: "abc" } }]]);
  await client.invoices.get("abc");
  assert.ok(calls[0].url.endsWith("/bill/receipts/abc/"));
  assert.equal(calls[0].method, "GET");
});

test("authorize() sends an empty body", async () => {
  const { client, calls } = makeClient([
    [200, {}, { success: true, data: { id: "abc", cae: "123", estado: "aprobado" } }],
  ]);
  const result = (await client.invoices.authorize("abc")) as any;
  assert.equal(calls[0].method, "POST");
  assert.ok(calls[0].url.endsWith("/bill/receipts/authorize/abc/"));
  assert.deepEqual(calls[0].body, {});
  assert.equal(result.data.cae, "123");
});

test("cancel() without motivo sends an empty body", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: {} }]]);
  await client.invoices.cancel("abc");
  assert.ok(calls[0].url.endsWith("/bill/receipts/cancel/abc/"));
  assert.deepEqual(calls[0].body, {});
});

test("cancel() with motivo", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: {} }]]);
  await client.invoices.cancel("abc", "Emitido por error");
  assert.deepEqual(calls[0].body, { motivo: "Emitido por error" });
});

test("supportedTypes()", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: [1, 6, 11] }]]);
  await client.invoices.supportedTypes();
  assert.ok(calls[0].url.endsWith("/bill/receipts/supported-types/"));
  assert.equal(calls[0].method, "GET");
});
