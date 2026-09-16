import assert from "node:assert/strict";
import { test } from "node:test";

import { RateLimitError, ServerError, VERSION, YoFacturo, type YoFacturoOptions } from "../src";
import { createFakeTransport, type QueuedResponse } from "../test-support/fake-transport";

function makeClient(responses: QueuedResponse[], options: Partial<YoFacturoOptions> = {}) {
  const { transport, calls } = createFakeTransport(responses);
  const client = new YoFacturo("yf_live_test_token", {
    transport,
    sleep: async () => {},
    ...options,
  });
  return { client, calls };
}

test("requires an api key", () => {
  assert.throws(() => new YoFacturo(""));
});

test("sends auth and user-agent headers", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { items: [] } }]]);
  await client.products.list();
  const headers = calls[0].headers;
  assert.equal(headers["X-API-Key"], "yf_live_test_token");
  assert.equal(headers["User-Agent"], `yofacturo-sdk-node/${VERSION}`);
});

test("never leaks the token in the thrown error", async () => {
  const { client } = makeClient([
    [401, {}, { success: false, error: "Invalid token", code: "UNAUTHORIZED" }],
  ]);
  await assert.rejects(
    () => client.products.list(),
    (err: Error) => {
      assert.ok(!String(err).includes("yf_live_test_token"));
      return true;
    }
  );
});

test("GET requests have no body", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: {} }]]);
  await client.customers.get("cust_1");
  assert.equal(calls[0].method, "GET");
  assert.equal(calls[0].body, null);
});

test("POST sends a JSON body", async () => {
  const { client, calls } = makeClient([[201, {}, { success: true, data: { _id: "p_1" } }]]);
  await client.products.create({ name: "Producto A", base_price: 100 });
  assert.deepEqual(calls[0].body, { name: "Producto A", base_price: 100 });
  assert.equal(calls[0].headers["Content-Type"], "application/json");
});

test("query params drop undefined values", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true, data: { items: [] } }]]);
  await client.customers.list({ page: 2, search: "acme" });
  assert.ok(calls[0].url.includes("page=2"));
  assert.ok(calls[0].url.includes("search=acme"));
});

test("retries on 429 then succeeds", async () => {
  const { client, calls } = makeClient([
    [429, { "Retry-After": "0" }, { success: false, error: "slow down", code: "RATE_LIMITED" }],
    [200, {}, { success: true, data: { items: [] } }],
  ]);
  const result = (await client.customers.list()) as { success: boolean };
  assert.equal(result.success, true);
  assert.equal(calls.length, 2);
});

test("retries on 5xx then succeeds", async () => {
  const { client, calls } = makeClient([
    [500, {}, { success: false, error: "boom", code: "INTERNAL_ERROR" }],
    [503, {}, { success: false, error: "unavailable", code: "SERVICE_UNAVAILABLE" }],
    [200, {}, { success: true, data: { items: [] } }],
  ]);
  await client.customers.list();
  assert.equal(calls.length, 3);
});

test("gives up after max retries", async () => {
  const responses: QueuedResponse[] = Array.from({ length: 4 }, () => [
    429,
    {},
    { success: false, error: "slow down", code: "RATE_LIMITED" },
  ]);
  const { client, calls } = makeClient(responses, { maxRetries: 3 });
  await assert.rejects(() => client.customers.list(), RateLimitError);
  assert.equal(calls.length, 4);
});

test("maxRetries 0 disables retries", async () => {
  const { client, calls } = makeClient(
    [[500, {}, { success: false, error: "boom", code: "INTERNAL_ERROR" }]],
    { maxRetries: 0 }
  );
  await assert.rejects(() => client.customers.list(), ServerError);
  assert.equal(calls.length, 1);
});

test("non-JSON-shaped error body does not crash", async () => {
  const client = new YoFacturo("yf_live_test_token", {
    sleep: async () => {},
    maxRetries: 0,
    transport: async () => ({ status: 502, headers: {}, body: "<html>Bad Gateway</html>" }),
  });
  await assert.rejects(() => client.customers.list(), ServerError);
});
