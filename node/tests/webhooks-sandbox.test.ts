import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { test } from "node:test";

import { YoFacturo, isSandboxKey, webhooks } from "../src";
import { createFakeTransport, type QueuedResponse } from "../test-support/fake-transport";

const SECRET = "whsec_test";
const BODY = '{"id":"evt_1","event":"invoice.authorized","data":{"id":"abc"}}';
const NOW = 1_760_000_000;

// Algoritmo del firmador saliente de la API, calculado a mano.
function sig(ts = NOW, body = BODY, secret = SECRET): string {
  return `t=${ts},v1=${createHmac("sha256", secret).update(`${ts}.${body}`).digest("hex")}`;
}

function makeClient(responses: QueuedResponse[], options = {}) {
  const { transport, calls } = createFakeTransport(responses);
  const client = new YoFacturo("yf_live_test_token", { transport, sleep: async () => {}, ...options });
  return { client, calls };
}

test("verifySignature accepts a valid signature (string and bytes)", () => {
  assert.equal(webhooks.verifySignature(SECRET, BODY, sig(), { now: NOW + 10 }), true);
  assert.equal(webhooks.verifySignature(SECRET, Buffer.from(BODY), sig(), { now: NOW }), true);
});

test("buildSignatureHeader matches the API algorithm", () => {
  assert.equal(webhooks.buildSignatureHeader(SECRET, NOW, BODY), sig());
});

test("verifySignature rejects bad headers, tampering and wrong secret", () => {
  for (const h of [undefined, null, "", "garbage", "t=abc,v1=ff", `t=${NOW}`, `t=${NOW},v1=${"0".repeat(64)}`, "v1=" + "0".repeat(64)]) {
    assert.equal(webhooks.verifySignature(SECRET, BODY, h, { now: NOW }), false, String(h));
  }
  assert.equal(webhooks.verifySignature(SECRET, BODY + " ", sig(), { now: NOW }), false);
  assert.equal(webhooks.verifySignature("otro", BODY, sig(), { now: NOW }), false);
});

test("verifySignature replay tolerance", () => {
  assert.equal(webhooks.verifySignature(SECRET, BODY, sig(), { now: NOW + 301 }), false);
  assert.equal(webhooks.verifySignature(SECRET, BODY, sig(), { now: NOW + 300 }), true);
  assert.equal(webhooks.verifySignature(SECRET, BODY, sig(), { now: NOW + 99999, toleranceSeconds: null }), true);
});

test("constructEvent returns the event or throws", () => {
  assert.equal(webhooks.constructEvent(SECRET, BODY, sig(), { now: NOW }).event, "invoice.authorized");
  assert.throws(() => webhooks.constructEvent(SECRET, BODY, "t=1,v1=00", { now: NOW }));
});

test("isSandboxKey / client.isSandbox", () => {
  assert.equal(isSandboxKey("yf_test_abc"), true);
  assert.equal(isSandboxKey("yf_live_abc"), false);
  assert.equal(isSandboxKey(undefined), false);
  assert.equal(new YoFacturo("yf_test_x").isSandbox, true);
  assert.equal(makeClient([]).client.isSandbox, false);
});

test("environment injects ambiente without overriding an explicit one", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true }], [200, {}, { success: true }]], { environment: "testing" });
  await client.invoices.create({ items: [] });
  assert.equal((calls[0].body as any).ambiente, "testing");
  await client.invoices.create({ items: [], ambiente: "production" });
  assert.equal((calls[1].body as any).ambiente, "production");
});

test("no environment leaves the body untouched; invalid environment throws", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true }]]);
  await client.invoices.create({ items: [] });
  assert.equal("ambiente" in (calls[0].body as object), false);
  assert.throws(() => new YoFacturo("k", { environment: "staging" as any }));
});

test("idempotencyKey header and invoices.link", async () => {
  const { client, calls } = makeClient([[200, {}, { success: true }], [200, {}, { success: true }]]);
  await client.invoices.create({ items: [] }, "k-1");
  assert.equal(calls[0].headers["Idempotency-Key"], "k-1");
  await client.invoices.link("abc");
  assert.equal(calls[1].method, "POST");
  assert.ok(calls[1].url.endsWith("/bill/receipts/abc/public-link/"));
});
