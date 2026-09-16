/**
 * Doble de prueba para `Transport`: reemplaza la red por una cola de
 * respuestas armadas a mano. No vive en `tests/` a propósito -- el test
 * runner de Node descubre automáticamente cualquier archivo dentro de un
 * directorio llamado `test`/`tests`, y este helper no tiene aserciones.
 */

import type { HttpMethod, Transport, TransportResponse } from "../src/client";

export interface RecordedCall {
  method: HttpMethod;
  url: string;
  headers: Record<string, string>;
  body: unknown;
  timeoutMs: number;
}

export type QueuedResponse = [number, Record<string, string>, unknown];

export function createFakeTransport(responses: QueuedResponse[]): {
  transport: Transport;
  calls: RecordedCall[];
} {
  const queue = [...responses];
  const calls: RecordedCall[] = [];

  const transport: Transport = async (method, url, headers, body) => {
    calls.push({
      method,
      url,
      headers: { ...headers },
      body: body ? JSON.parse(body) : null,
      timeoutMs: 0,
    });
    const next = queue.shift();
    if (!next) {
      throw new Error("FakeTransport se quedó sin respuestas encoladas");
    }
    const [status, respHeaders, payload] = next;
    return { status, headers: respHeaders, body: payload } as TransportResponse;
  };

  return { transport, calls };
}
