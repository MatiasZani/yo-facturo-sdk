import assert from "node:assert/strict";
import { test } from "node:test";

import { YoFacturo } from "../src";
import { createFakeTransport, type QueuedResponse } from "../test-support/fake-transport";

const RESOURCES = [
  "customers",
  "products",
  "sales",
  "services",
  "rentals",
  "appointments",
  "subscriptionPlans",
] as const;
const BASES: Record<(typeof RESOURCES)[number], string> = {
  customers: "/customers",
  products: "/products",
  sales: "/sales",
  services: "/services",
  rentals: "/rentals",
  appointments: "/appointments",
  subscriptionPlans: "/subscription-plans",
};
// Recursos con listados multi-moneda: list() envia currency_aware=1 por defecto.
const CURRENCY_AWARE = new Set<string>(["products", "services", "rentals"]);

function makeClient(responses: QueuedResponse[]) {
  const { transport, calls } = createFakeTransport(responses);
  const client = new YoFacturo("yf_live_test_token", { transport, sleep: async () => {} });
  return { client, calls };
}

for (const name of RESOURCES) {
  test(`${name}.list() -- GET {base}/list/`, async () => {
    const { client, calls } = makeClient([[200, {}, { success: true, data: { items: [], total: 0 } }]]);
    await client[name].list({ page: 1, per_page: 10 });
    assert.equal(calls[0].method, "GET");
    const aware = CURRENCY_AWARE.has(name) ? "&currency_aware=1" : "";
    assert.ok(calls[0].url.endsWith(`${BASES[name]}/list/?page=1&per_page=10${aware}`));
  });

  test(`${name}.get() -- GET {base}/{id}/`, async () => {
    const { client, calls } = makeClient([[200, {}, { success: true, data: { _id: "x" } }]]);
    await client[name].get("x");
    assert.equal(calls[0].method, "GET");
    assert.ok(calls[0].url.endsWith(`${BASES[name]}/x/`));
  });

  test(`${name}.create() -- POST {base}/`, async () => {
    const { client, calls } = makeClient([[201, {}, { success: true, data: { _id: "new" } }]]);
    await client[name].create({ name: "Test" });
    assert.equal(calls[0].method, "POST");
    assert.ok(calls[0].url.endsWith(`${BASES[name]}/`));
    assert.deepEqual(calls[0].body, { name: "Test" });
  });

  test(`${name}.update() is partial -- PUT {base}/{id}/`, async () => {
    const { client, calls } = makeClient([[200, {}, { success: true, data: { _id: "x" } }]]);
    await client[name].update("x", { price: 1500, description: null });
    assert.equal(calls[0].method, "PUT");
    assert.ok(calls[0].url.endsWith(`${BASES[name]}/x/`));
    assert.deepEqual(calls[0].body, { price: 1500, description: null });
  });

  test(`${name}.delete() -- DELETE {base}/{id}/`, async () => {
    const { client, calls } = makeClient([[200, {}, { success: true, data: { deleted: true } }]]);
    await client[name].delete("x");
    assert.equal(calls[0].method, "DELETE");
    assert.ok(calls[0].url.endsWith(`${BASES[name]}/x/`));
    assert.equal(calls[0].body, null);
  });
}

test("products.create() supports an idempotency key", async () => {
  const { client, calls } = makeClient([[201, {}, { success: true, data: { _id: "new" } }]]);
  await client.products.create({ name: "Test" }, "op-001");
  assert.equal(calls[0].headers["Idempotency-Key"], "op-001");
});

test("sales.create() supports an idempotency key", async () => {
  const { client, calls } = makeClient([[201, {}, { success: true, data: { _id: "new" } }]]);
  await client.sales.create({ items: [] }, "op-002");
  assert.equal(calls[0].headers["Idempotency-Key"], "op-002");
});

test("products.list() sends currency_aware=1 by default and can opt out", async () => {
  const { client, calls } = makeClient([
    [200, {}, { success: true, data: { items: [] } }],
    [200, {}, { success: true, data: { items: [] } }],
  ]);
  await client.products.list();
  assert.ok(calls[0].url.endsWith("/products/list/?currency_aware=1"));
  await client.products.list({ currency_aware: false, page: 2 });
  assert.ok(calls[1].url.endsWith("/products/list/?page=2"));
});

for (const name of ["services", "rentals"] as const) {
  test(`${name}.list() sends currency_aware=1 by default and can opt out`, async () => {
    const { client, calls } = makeClient([
      [200, {}, { success: true, data: { items: [] } }],
      [200, {}, { success: true, data: { items: [] } }],
    ]);
    await client[name].list();
    assert.ok(calls[0].url.endsWith(`${BASES[name]}/list/?currency_aware=1`));
    await client[name].list({ currency_aware: false, page: 2 });
    assert.ok(calls[1].url.endsWith(`${BASES[name]}/list/?page=2`));
  });
}

for (const name of ["appointments", "subscriptionPlans"] as const) {
  test(`${name}.list() does not send currency_aware`, async () => {
    const { client, calls } = makeClient([[200, {}, { success: true, data: { items: [] } }]]);
    await client[name].list();
    assert.ok(!calls[0].url.includes("currency_aware"));
  });
}
