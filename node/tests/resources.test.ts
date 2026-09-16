import assert from "node:assert/strict";
import { test } from "node:test";

import { YoFacturo } from "../src";
import { createFakeTransport, type QueuedResponse } from "../test-support/fake-transport";

const RESOURCES = ["customers", "products", "sales"] as const;
const BASES: Record<(typeof RESOURCES)[number], string> = {
  customers: "/customers",
  products: "/products",
  sales: "/sales",
};

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
    assert.ok(calls[0].url.endsWith(`${BASES[name]}/list/?page=1&per_page=10`));
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
