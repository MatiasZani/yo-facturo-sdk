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
   * Obligatorios: `punto_venta`, `tipo_documento`, `numero_documento` e
   * `items`. `concepto` (1 = productos, 2 = servicios, 3 = ambos) también lo
   * exige la API: el SDK manda `concepto: 1` si no lo pasás.
   * `tipo_comprobante` (A/B/C) se infiere de la condición de IVA del emisor y
   * del receptor si se omite.
   *
   * Los `precio_unitario` de `items` son precios FINALES (IVA incluido, como
   * en el POS) y el backend calcula neto, IVA y total: no hace falta mandar
   * `importe_*` ni `iva_items`. Para mandar precios NETOS de IVA pasá
   * `precios_con_iva: false`.
   *
   * La condición de IVA del receptor se resuelve con la misma regla que el
   * POS: pasá `condicion_iva_receptor_id` (código ARCA: 1 RI, 4 Exento,
   * 5 Consumidor Final, 6 Monotributo) o, equivalentes,
   * `receptor_condicion_iva` / `condicion_iva` con el nombre. Con un CUIT
   * solo, la API consulta el padrón de ARCA; si no puede determinarla emite
   * Factura B a Consumidor Final.
   *
   * Con `autorizar: true` la autorización ante AFIP se dispara en segundo
   * plano: la respuesta vuelve con `authorization_pending: true` y hay que
   * releer el comprobante (`get`) hasta que el campo `cae` venga cargado. Con
   * `autorizar: false` (default) el comprobante queda en borrador para
   * autorizar después con `authorize()`. `idempotencyKey` es opcional: evita
   * duplicar el comprobante si necesitás reintentar tras un timeout de red.
   */
  create<T = any>(fields: Record<string, unknown>, idempotencyKey?: string): Promise<T> {
    return this.client.post<T>(`${BASE}/invoice/`, { concepto: 1, ...fields }, idempotencyKey);
  }

  /**
   * Emite una factura a un cliente ya registrado --
   * `POST /bill/receipts/invoice/customer/`. La API toma documento, razón
   * social y condición de IVA de la ficha del cliente (`customerId`), así que
   * no se mandan `tipo_documento`, `numero_documento` ni la condición.
   * Obligatorios: `punto_venta` e `items` (`concepto` va en 1 si no lo pasás).
   * Los precios, `precios_con_iva` y `autorizar` funcionan igual que en
   * `create()`. A diferencia de `create()`, la respuesta trae el id del
   * comprobante en `data.factura_id` (no en `data.id`).
   */
  createForCustomer<T = any>(
    customerId: string,
    fields: Record<string, unknown> = {},
    idempotencyKey?: string
  ): Promise<T> {
    return this.client.post<T>(
      `${BASE}/invoice/customer/`,
      { concepto: 1, ...fields, customer_id: customerId },
      idempotencyKey
    );
  }

  /**
   * Emite una nota de crédito -- `POST /bill/receipts/credit-note/`.
   * `comprobanteAsociadoId` es el `id` del comprobante original, que debe
   * estar aprobado. Cuánto acreditar se indica con UNO de estos campos de
   * `fields`:
   *
   * - `lineas: [{ linea: 1, cantidad: 1 }]`: devolución por renglón. `linea` es
   *   el índice (desde 0) del renglón del comprobante original y `cantidad`
   *   cuántas unidades se devuelven. El backend calcula neto e IVA.
   * - `importe_a_acreditar: 605`: un monto (bonificación, ajuste de precio).
   * - `porcentaje_aplicar: 50`: un porcentaje del comprobante (0 a 100].
   * - Ninguno: anula el 100% del comprobante.
   *
   * Firma: `creditNote(id, fields)` o, compatible con la anterior,
   * `creditNote(id, items, fields)`. `items` ya no sirve para devoluciones
   * parciales: la API calcula las líneas de la nota a partir del original y
   * un `items` que no coincida con el total de la nota se rechaza con 400.
   */
  creditNote<T = any>(comprobanteAsociadoId: string, fields?: Record<string, unknown>): Promise<T>;
  creditNote<T = any>(
    comprobanteAsociadoId: string,
    items: InvoiceItem[] | null | undefined,
    fields?: Record<string, unknown>
  ): Promise<T>;
  creditNote<T = any>(
    comprobanteAsociadoId: string,
    itemsOrFields?: InvoiceItem[] | Record<string, unknown> | null,
    maybeFields: Record<string, unknown> = {}
  ): Promise<T> {
    const items = Array.isArray(itemsOrFields) ? itemsOrFields : undefined;
    const fields = Array.isArray(itemsOrFields) ? maybeFields : { ...(itemsOrFields ?? {}), ...maybeFields };
    return this.client.post<T>(`${BASE}/credit-note/`, {
      comprobante_asociado_id: comprobanteAsociadoId,
      ...(items ? { items } : {}),
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
   * Link público firmado para compartir el comprobante (PDF/HTML) sin login --
   * `POST /bill/receipts/{id}/public-link/`. El comprobante debe estar aprobado.
   */
  link<T = any>(comprobanteId: string): Promise<T> {
    return this.client.post<T>(`${BASE}/${comprobanteId}/public-link/`, {});
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
