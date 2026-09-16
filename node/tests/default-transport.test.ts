/**
 * A diferencia del resto de los tests (que inyectan un `transport` falso),
 * estos dos ejercitan el transporte real -- el que usa el `fetch` global de
 * Node -- mockeando `globalThis.fetch`. Sigue sin haber red real.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { YoFacturo } from "../src";

test("default transport uses global fetch and parses the JSON response", async (t) => {
  const originalFetch = globalThis.fetch;
  const requests: Array<{ url: string; init: RequestInit }> = [];

  globalThis.fetch = (async (url: any, init: any) => {
    requests.push({ url: String(url), init });
    return new Response(JSON.stringify({ success: true, data: { items: [] } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }) as typeof fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  const client = new YoFacturo("yf_live_test_token", { sleep: async () => {} });
  const result = (await client.customers.list()) as { success: boolean };

  assert.equal(result.success, true);
  assert.equal(requests.length, 1);
  const headers = requests[0].init.headers as Record<string, string>;
  assert.equal(headers["X-API-Key"], "yf_live_test_token");
  assert.ok(requests[0].url.includes("/customers/list/"));
});

test("default transport maps a non-2xx response to a typed error", async (t) => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () =>
    new Response(JSON.stringify({ success: false, error: "not found", code: "NOT_FOUND" }), {
      status: 404,
    })) as typeof fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  const client = new YoFacturo("yf_live_test_token", { sleep: async () => {} });
  await assert.rejects(
    () => client.customers.get("missing"),
    (err: any) => {
      assert.equal(err.statusCode, 404);
      assert.equal(err.code, "NOT_FOUND");
      return true;
    }
  );
});
