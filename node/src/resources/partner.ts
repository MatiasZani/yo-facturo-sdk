/**
 * Cuentas API partner -- `/partner`.
 *
 * Solo para cuentas con contrato partner (cualquier otra recibe 403 con
 * `error_code: "API_PARTNER_REQUIRED"`). Flujo: `createTaxpayer(...)` registra
 * el CUIT de tu usuario final, el usuario delega WSFE al CUIT de YoFacturo,
 * `verifyDelegation(id)` lo confirma y después se factura con
 * `client.invoices.create({ taxpayer_id: id, ... })`.
 *
 * Scopes: `taxpayers:read` para leer, `taxpayers:write` para registrar, dar de
 * baja y verificar la delegación (solo los ve una cuenta partner).
 * Guía: https://yo-facturo.com/dev/ (sección «Cuentas API partner»).
 */

import type { YoFacturo } from "../client";

const BASE = "/partner";

export interface PartnerTaxpayerParams {
  /** Condición frente al IVA del usuario final, p. ej. `"monotributo"`. */
  tax_condition?: string;
  /** Punto de venta habilitado para WSFE. */
  punto_venta?: string;
  business_name?: string;
  [key: string]: unknown;
}

export interface PartnerListParams {
  /** Tamaño de página (máx. 500). */
  limit?: number;
  /** `next_cursor` de la página anterior. */
  cursor?: string;
  /** Busca por CUIT o razón social. */
  q?: string;
}

function compact(fields: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== undefined));
}

export class PartnerResource {
  constructor(private readonly client: YoFacturo) {}

  /**
   * Registra el CUIT de un usuario final -- `POST /partner/taxpayers/` (`taxpayers:write`).
   * El `id` devuelto es el `taxpayer_id` para facturar. Errores:
   * `API_PARTNER_TAXPAYER_CUIT_INVALID` (400), `API_PARTNER_TAXPAYER_DUPLICATE` /
   * `API_PARTNER_TAXPAYER_CUIT_CLAIMED` (409).
   */
  createTaxpayer<T = any>(taxId: string, params: PartnerTaxpayerParams = {}): Promise<T> {
    return this.client.post<T>(`${BASE}/taxpayers/`, { tax_id: taxId, ...compact(params) });
  }

  /**
   * Lista los CUIT activos -- `GET /partner/taxpayers/` (`taxpayers:read`).
   * Paginación por cursor: pasá `data.next_cursor` como `cursor` hasta que venga `null`.
   */
  listTaxpayers<T = any>(params: PartnerListParams = {}): Promise<T> {
    return this.client.get<T>(`${BASE}/taxpayers/`, compact({ ...params }));
  }

  /** Un CUIT registrado -- `GET /partner/taxpayers/{taxpayerId}/` (`taxpayers:read`). */
  getTaxpayer<T = any>(taxpayerId: string): Promise<T> {
    return this.client.get<T>(`${BASE}/taxpayers/${taxpayerId}/`);
  }

  /**
   * Baja lógica de un CUIT -- `DELETE /partner/taxpayers/{taxpayerId}/` (`taxpayers:write`).
   * No se pueden emitir comprobantes nuevos con él; los emitidos conservan su historial.
   */
  removeTaxpayer<T = any>(taxpayerId: string): Promise<T> {
    return this.client.delete<T>(`${BASE}/taxpayers/${taxpayerId}/`);
  }

  /**
   * Verifica la delegación WSFE de un CUIT --
   * `POST /partner/taxpayers/{taxpayerId}/verify-delegation/` (`taxpayers:write`, máx. 60/min).
   * `data.delegation_verified` es `true`, `false` o `null` (ARCA no contestó: reintentá).
   */
  verifyDelegation<T = any>(taxpayerId: string): Promise<T> {
    return this.client.post<T>(`${BASE}/taxpayers/${taxpayerId}/verify-delegation/`, {});
  }

  /** CUIT activos del período y estimado en ARS -- `GET /partner/usage/` (`taxpayers:read`). */
  usage<T = any>(): Promise<T> {
    return this.client.get<T>(`${BASE}/usage/`);
  }
}
