import assert from "node:assert/strict";
import { test } from "node:test";

import { YoFacturo } from "../src";
import { createFakeTransport, type QueuedResponse } from "../test-support/fake-transport";

const TP = "6650f2c1a1b2c3d4e5f60718";
const OK: QueuedResponse[] = [[200, {}, { success: true, data: {} }]];

async function call(invoke: (c: YoFacturo) => Promise<unknown>) {
  const { transport, calls } = createFakeTransport(OK);
  const client = new YoFacturo("yf_live_test_token", { transport, sleep: async () => {} });
  await invoke(client);
  return calls[0];
}

test("createTaxpayer() posts tax_id and only the given fields", async () => {
  const c = await call((client) =>
    client.partner.createTaxpayer("20111111112", { tax_condition: "monotributo", punto_venta: "2", business_name: undefined })
  );
  assert.equal(c.method, "POST");
  assert.ok(c.url.endsWith("/partner/taxpayers/"));
  assert.deepEqual(c.body, { tax_id: "20111111112", tax_condition: "monotributo", punto_venta: "2" });
});

test("listTaxpayers() sends only the given params", async () => {
  const c = await call((client) => client.partner.listTaxpayers({ limit: 100, q: "cliente", cursor: undefined }));
  assert.equal(c.method, "GET");
  const [path, query] = c.url.split("?");
  assert.ok(path.endsWith("/partner/taxpayers/"));
  assert.ok(query.includes("limit=100") && query.includes("q=cliente") && !query.includes("cursor"));
});

test("get / remove / verifyDelegation / usage hit their routes", async () => {
  const get = await call((client) => client.partner.getTaxpayer(TP));
  assert.equal(get.method, "GET");
  assert.ok(get.url.endsWith(`/partner/taxpayers/${TP}/`));
  const rm = await call((client) => client.partner.removeTaxpayer(TP));
  assert.equal(rm.method, "DELETE");
  assert.ok(rm.url.endsWith(`/partner/taxpayers/${TP}/`));
  const ver = await call((client) => client.partner.verifyDelegation(TP));
  assert.equal(ver.method, "POST");
  assert.ok(ver.url.endsWith(`/partner/taxpayers/${TP}/verify-delegation/`));
  const usage = await call((client) => client.partner.usage());
  assert.equal(usage.method, "GET");
  assert.ok(usage.url.endsWith("/partner/usage/"));
});
