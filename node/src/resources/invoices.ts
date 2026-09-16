/**
 * Comprobantes electrónicos AFIP/ARCA -- `/bill/receipts`.
 *
 * Scope requerido: `invoices:read` para leer, `invoices:write` para emitir
 * o modificar comprobantes. Guía completa: https://yo-facturo.com/dev/invoices/
 */

import type { YoFacturo } from "../client";
import type { ListParams } from "./base";

const BASE = "/bill/receipts";

export interface InvoiceItem {
  descripcion?: string;
  cantidad?: number;
  precio_unitario?: number;
  [key: string]: unknown;
}

export interface InvoiceListParams extends ListParams {
  tipo_comprobante?: number;
  estado?: string;
}

export class InvoicesResource {
  constructor(private readonly client: YoFacturo) {}

  /**
   * Emite un comprobante -- `POST /bill/receipts/invoice/`.
   *
   * `tipo_documento`, `numero_documento` e `items` son obligatorios;
   * `tipo_comprobante` (A/B/C) se infiere de la condición de IVA del emisor
   * si se omite. Con `autorizar: true` la autorización ante AFIP se dispara
   * en segundo plano: la respuesta vuelve con `authorization_pending: true`
   * y hay que releer el comprobante (`get`) hasta que el campo `cae` venga
   * cargado. Con `autorizar: false` (default) el comprobante queda en
   * borrador para autorizar después con `authorize()`. `idempotencyKey` es
   * opcional: evita duplicar el comprobante si necesitás reintentar tras un
   * timeout de red.
   */
  create<T = any>(fields: Record<string, unknown>, idempotencyKey?: string): Promise<T> {
    return this.client.post<T>(`${BASE}/invoice/`, fields, idempotencyKey);
  }

  /**
   * Emite una factura a un cliente ya registrado. Usa el mismo endpoint que
   * `create()`, pero resuelve los datos fiscales del receptor a partir de
   * `customerId` en vez de mandarlos sueltos.
   */
  createForCustomer<T = any>(
    customerId: string,
    fields: Record<string, unknown> = {},
    idempotencyKey?: string
  ): Promise<T> {
    return this.create<T>({ customer_id: customerId, ...fields }, idempotencyKey);
  }

  /**
   * Emite una nota de crédito -- `POST /bill/receipts/credit-note/`.
   * `comprobanteAsociadoId` (el `id` del comprobante original, que debe
   * estar aprobado) e `items` son obligatorios.
   */
  creditNote<T = any>(
    comprobanteAsociadoId: string,
    items: InvoiceItem[],
    fields: Record<string, unknown> = {}
  ): Promise<T> {
    return this.client.post<T>(`${BASE}/credit-note/`, {
      comprobante_asociado_id: comprobanteAsociadoId,
      items,
      ...fields,
    });
  }

  /** Emite una nota de débito -- `POST /bill/receipts/debit-note/`. */
  debitNote<T = any>(
    comprobanteAsociadoId: string,
    items: InvoiceItem[],
    fields: Record<string, unknown> = {}
  ): Promise<T> {
    return this.client.post<T>(`${BASE}/debit-note/`, {
      comprobante_asociado_id: comprobanteAsociadoId,
      items,
      ...fields,
    });
  }

  /** Lista comprobantes con paginación y filtros -- `GET /bill/receipts/list/`. */
  list<T = any>(params: InvoiceListParams = {}): Promise<T> {
    return this.client.get<T>(`${BASE}/list/`, params);
  }

  /** Obtiene un comprobante por su id -- `GET /bill/receipts/{id}/`. */
  get<T = any>(comprobanteId: string): Promise<T> {
    return this.client.get<T>(`${BASE}/${comprobanteId}/`);
  }

  /**
   * Autoriza un comprobante en borrador ante AFIP (obtiene el CAE) --
   * `POST /bill/receipts/authorize/{id}/`. A diferencia de `create()` con
   * `autorizar: true`, esta llamada es síncrona: espera a AFIP y, si lo
   * aprueba, la respuesta ya trae `cae` y `cae_vencimiento`. Si AFIP lo
   * rechaza, lanza `ValidationError` con el motivo.
   */
  authorize<T = any>(comprobanteId: string): Promise<T> {
    return this.client.post<T>(`${BASE}/authorize/${comprobanteId}/`, {});
  }

  /**
   * Anula un comprobante ya autorizado -- `POST /bill/receipts/cancel/{id}/`.
   * Genera automáticamente una nota de crédito por el importe total del
   * comprobante original (viene en `data.nota_credito` de la respuesta).
   */
  cancel<T = any>(comprobanteId: string, motivo?: string): Promise<T> {
    return this.client.post<T>(`${BASE}/cancel/${comprobanteId}/`, motivo ? { motivo } : {});
  }

  /**
   * Tipos de comprobante soportados según la condición fiscal del emisor --
   * `GET /bill/receipts/supported-types/`.
   */
  supportedTypes<T = any>(): Promise<T> {
    return this.client.get<T>(`${BASE}/supported-types/`);
  }
}
