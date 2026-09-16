import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ApiError,
  AuthenticationError,
  ConflictError,
  NotFoundError,
  PermissionError,
  RateLimitError,
  ScopeError,
  ServerError,
  ValidationError,
  YoFacturo,
} from "../src";
import { createFakeTransport, type QueuedResponse } from "../test-support/fake-transport";

function makeClient(responses: QueuedResponse[], maxRetries = 0) {
  const { transport } = createFakeTransport(responses);
  return new YoFacturo("yf_live_test_token", { transport, sleep: async () => {}, maxRetries });
}

const cases: Array<[number, string, new (...args: any[]) => ApiError]> = [
  [401, "UNAUTHORIZED", AuthenticationError],
  [403, "FORBIDDEN", ScopeError],
  [404, "NOT_FOUND", NotFoundError],
  [400, "BAD_REQUEST", ValidationError],
  [400, "VALIDATION_ERROR", ValidationError],
  [422, "UNPROCESSABLE_ENTITY", ValidationError],
  [409, "CONFLICT", ConflictError],
  [429, "RATE_LIMITED", RateLimitError],
  [500, "INTERNAL_ERROR", ServerError],
  [503, "SERVICE_UNAVAILABLE", ServerError],
];

for (const [status, code, ExpectedError] of cases) {
  test(`status ${status} (${code}) maps to ${ExpectedError.name}`, async () => {
    const client = makeClient([[status, {}, { success: false, error: "boom", code }]]);
    await assert.rejects(
      () => client.customers.get("x"),
      (err: any) => {
        assert.ok(err instanceof ExpectedError, `expected ${ExpectedError.name}, got ${err.constructor.name}`);
        assert.equal(err.statusCode, status);
        assert.equal(err.code, code);
        assert.equal(err.message, "boom");
        return true;
      }
    );
  });
}

test("PermissionError is a ScopeError", () => {
  const err = new PermissionError("nope");
  assert.ok(err instanceof ScopeError);
});

test("ValidationError carries field errors", async () => {
  const client = makeClient([
    [
      400,
      {},
      {
        success: false,
        error: "Validation failed",
        code: "VALIDATION_ERROR",
        errors: [{ field: "name", message: "This field is required" }],
      },
    ],
  ]);
  await assert.rejects(
    () => client.customers.create({}),
    (err: any) => {
      assert.deepEqual(err.errors, [{ field: "name", message: "This field is required" }]);
      return true;
    }
  );
});

test("RateLimitError parses retryAfter from the Retry-After header", async () => {
  const client = makeClient([
    [429, { "Retry-After": "12" }, { success: false, error: "slow down", code: "RATE_LIMITED" }],
  ]);
  await assert.rejects(
    () => client.customers.get("x"),
    (err: any) => {
      assert.equal(err.retryAfter, 12);
      return true;
    }
  );
});

test("RateLimitError retryAfter is undefined without the header", async () => {
  const client = makeClient([[429, {}, { success: false, error: "slow down", code: "RATE_LIMITED" }]]);
  await assert.rejects(
    () => client.customers.get("x"),
    (err: any) => {
      assert.equal(err.retryAfter, undefined);
      return true;
    }
  );
});
