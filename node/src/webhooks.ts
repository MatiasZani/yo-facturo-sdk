/**
 * Verificación de firmas de webhooks de YoFacturo.
 *
 * Algoritmo (idéntico al firmador saliente de la API):
 *   X-YF-Signature: t=<unix_ts>,v1=<hex>
 *   hex = HMAC_SHA256(secret, "<t>." + <body crudo>)
 *
 * Hay que firmar sobre los BYTES CRUDOS recibidos, no sobre el JSON
 * re-serializado.
 */

import { createHmac, timingSafeEqual } from "node:crypto";

export const SIGNATURE_HEADER = "X-YF-Signature";
export const DEFAULT_TOLERANCE_SECONDS = 300;

export type Payload = string | Uint8Array;

export function parseSignatureHeader(header?: string | null): { timestamp?: number; signature?: string } {
  if (!header) return {};
  let timestamp: number | undefined;
  let signature: string | undefined;
  for (const raw of header.split(",")) {
    const idx = raw.indexOf("=");
    if (idx < 0) continue;
    const key = raw.slice(0, idx).trim();
    const value = raw.slice(idx + 1).trim();
    if (key === "t") {
      if (!/^-?\d+$/.test(value)) return {};
      timestamp = Number(value);
    } else if (key === "v1") {
      signature = value;
    }
  }
  return { timestamp, signature };
}

export function computeSignature(secret: string, timestamp: number, payload: Payload): string {
  return createHmac("sha256", secret)
    .update(`${timestamp}.`)
    .update(payload)
    .digest("hex");
}

export function buildSignatureHeader(secret: string, timestamp: number, payload: Payload): string {
  return `t=${timestamp},v1=${computeSignature(secret, timestamp, payload)}`;
}

export interface VerifyOptions {
  /** Diferencia máxima con la hora actual en segundos (default 300). `null` desactiva el chequeo. */
  toleranceSeconds?: number | null;
  /** Hora actual inyectable en segundos (tests). */
  now?: number;
}

/** true si la firma es válida. Nunca lanza por una firma inválida. */
export function verifySignature(
  secret: string,
  payload: Payload,
  signatureHeader: string | null | undefined,
  options: VerifyOptions = {}
): boolean {
  const { timestamp, signature } = parseSignatureHeader(signatureHeader);
  if (timestamp === undefined || !signature || !secret) return false;
  const tolerance = options.toleranceSeconds === undefined ? DEFAULT_TOLERANCE_SECONDS : options.toleranceSeconds;
  if (tolerance !== null) {
    const now = options.now ?? Date.now() / 1000;
    if (Math.abs(now - timestamp) > tolerance) return false;
  }
  const expected = Buffer.from(computeSignature(secret, timestamp, payload), "utf8");
  const received = Buffer.from(signature, "utf8");
  return expected.length === received.length && timingSafeEqual(expected, received);
}

/** Verifica la firma y devuelve el evento parseado; lanza `Error` si no es válida. */
export function constructEvent<T = any>(
  secret: string,
  payload: Payload,
  signatureHeader: string | null | undefined,
  options: VerifyOptions = {}
): T {
  if (!verifySignature(secret, payload, signatureHeader, options)) {
    throw new Error("Firma de webhook inválida");
  }
  const text = typeof payload === "string" ? payload : Buffer.from(payload).toString("utf8");
  return JSON.parse(text) as T;
}
