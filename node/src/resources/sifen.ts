/**
 * Facturación electrónica de Paraguay (SIFEN) -- `/bill/sifen`.
 *
 * La emisión sale por `client.sales.create({ ..., request_fiscal_document: true })`
 * (o `generateInvoice()` sobre una venta existente) y es asíncrona: la respuesta
 * no trae el CDC, hay que releer la venta (`client.sales.get(id)`, campo
 * `fiscal`) o este recurso (`get(cdc)`) hasta que `status` sea `approved`, o
 * suscribirse a los webhooks `invoice.authorized` / `invoice.rejected` /
 * `invoice.cancelled` (`system: "sifen"`).
 *
 * Scope requerido: `invoices:read` para leer, `invoices:write` para operar
 * documentos, `accounting:read|write` para la configuración (certificados,
 * ambiente, numeración), `received_invoices:write` para los eventos del
 * receptor. Un token `yf_test_*` lee todo pero nunca transmite a SIFEN (409).
 * Guía completa: https://yo-facturo.com/dev/paraguay-sifen/
 *
 * Fuera del SDK: la subida del certificado PKCS#12 (`multipart/form-data`) y
 * la descarga del XML firmado (`application/xml`); usá HTTP directo, ver la guía.
 */

import type { YoFacturo } from "../client";

const BASE = "/bill/sifen";

export interface SifenListParams {
  tipo_de?: number;
  /** Uno o varios estados separados por coma: `"approved,approved_obs"`. */
  status?: string;
  date_from?: string;
  date_to?: string;
  sale_id?: string;
  cdc?: string;
  /** `"<establecimiento>-<punto>"`, p. ej. `"001-002"`. */
  caja?: string;
  limit?: number;
  cursor?: string;
  [key: string]: unknown;
}

export interface SifenDebitNoteItem {
  descripcion: string;
  /** Importe BRUTO (IVA incluido) en guaraníes, entero positivo. */
  importe: number;
  /** 10, 5 o 0 (exento). */
  tasa_iva: 10 | 5 | 0;
  cantidad?: number;
}

export interface SifenCreateItem {
  descripcion: string;
  /** Default 1; hasta 3 decimales. */
  cantidad?: number;
  /** Precio unitario BRUTO (IVA incluido) en guaraníes: usar este O `importe`. */
  precio_unitario?: number;
  /** Total BRUTO de la línea en guaraníes enteros. */
  importe?: number;
  /** 10, 5 o 0 (exento); default 10. */
  tasa_iva?: 10 | 5 | 0;
  codigo?: string;
}

export interface SifenCreateDocument {
  items: SifenCreateItem[];
  tipo_de?: number;
  receptor?: { document_type: "ruc" | "ci" | "none"; document_number?: string; name?: string; email?: string; phone?: string };
  condicion?: "contado" | "credito";
  pago_tipo?: number;
  plazo_dias?: number;
  sales_point_id?: string;
  establecimiento?: string;
  punto_expedicion?: string;
  info_emisor?: string;
  client_reference?: string;
}

export interface SifenVerifyCaja {
  establecimiento?: string;
  punto_expedicion?: string;
  sales_point_id?: string;
  tipo_de?: number;
  /** `false` omite la consulta del RUC emisor a SIFEN. */
  check_ruc?: boolean;
}

export interface SifenNumberingParams {
  tipo_de?: number;
  timbrado?: string;
  est?: string;
  punExp?: string;
}

export interface SifenCreditNoteLine {
  /** Índice (desde 0) del renglón de la factura. */
  linea: number;
  cantidad: number;
}

function compact(fields: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== undefined));
}

export class SifenResource {
  constructor(private readonly client: YoFacturo) {}

  // -- documentos ---------------------------------------------------------

  /**
   * Lista documentos SIFEN, el más nuevo primero -- `GET /bill/sifen/documents/`.
   * La paginación es por cursor: pasá `data.next_cursor` como `cursor` hasta
   * que venga `null`.
   */
  list<T = any>(params: SifenListParams = {}): Promise<T> {
    return this.client.get<T>(`${BASE}/documents/`, params);
  }

  /**
   * Emite una factura electrónica (FE, `tipo_de` 1) SIN venta --
   * `POST /bill/sifen/documents/`. Cada ítem trae `precio_unitario` o `importe`
   * BRUTO (IVA incluido, guaraníes enteros) y `tasa_iva`: el backend calcula
   * base, IVA y total. Caja: `sales_point_id` o `establecimiento` +
   * `punto_expedicion`. `client_reference` repite el mismo documento sin numerar
   * otro. Es asíncrona: la respuesta trae el CDC en estado `signed`; leé
   * `get(cdc)` hasta `approved`. Solo la FE (1); las notas usan `debitNote` y `creditNote`.
   */
  create<T = any>(fields: SifenCreateDocument, idempotencyKey?: string): Promise<T> {
    return this.client.post<T>(`${BASE}/documents/`, { tipo_de: 1, ...compact({ ...fields }) }, idempotencyKey);
  }

  /**
   * Obtiene un documento por su CDC (44 dígitos) -- `GET /bill/sifen/documents/{cdc}/`.
   * Trae `status`, número, timbrado, totales, QR, protocolo, `sifen_messages`
   * (cada `dCodRes`/`dMsgRes` que contestó SIFEN: el motivo de un rechazo) y
   * los eventos del documento.
   */
  get<T = any>(cdc: string): Promise<T> {
    return this.client.get<T>(`${BASE}/documents/${cdc}/`);
  }

  /**
   * Consulta el documento en vivo a SIFEN (siConsDE) --
   * `POST /bill/sifen/documents/{cdc}/consulta/`. Actualiza el estado local si
   * SIFEN ya lo aprobó. Si SIFEN no responde lanza `ServerError` (503) y el
   * estado local no cambia. Límite: 30 por minuto.
   */
  query<T = any>(cdc: string): Promise<T> {
    return this.client.post<T>(`${BASE}/documents/${cdc}/consulta/`, {});
  }

  /** Historial de eventos de un documento -- `GET /bill/sifen/documents/{cdc}/events/`. */
  events<T = any>(cdc: string): Promise<T> {
    return this.client.get<T>(`${BASE}/documents/${cdc}/events/`);
  }

  /**
   * Anula un documento -- `POST /bill/sifen/documents/{cdc}/void/`. Según el
   * estado: cancelación (FE aprobada hace menos de 48 h), nota de crédito por
   * el saldo (fuera de ventana) o inutilización (número nunca aprobado);
   * `data.action` dice cuál se hizo. `reason`: 5 a 500 caracteres.
   */
  void<T = any>(cdc: string, reason: string, idempotencyKey?: string): Promise<T> {
    return this.client.post<T>(`${BASE}/documents/${cdc}/void/`, { reason }, idempotencyKey);
  }

  /** Calcula la nota de débito sin emitirla -- `POST /bill/sifen/documents/{cdc}/debit-note/preview/`. */
  debitNotePreview<T = any>(cdc: string, items: SifenDebitNoteItem[], motivo?: number): Promise<T> {
    return this.client.post<T>(`${BASE}/documents/${cdc}/debit-note/preview/`, { items, ...compact({ motivo }) });
  }

  /**
   * Emite una nota de débito electrónica (NDE) --
   * `POST /bill/sifen/documents/{cdc}/debit-note/`. `cdc` es el de la factura
   * (FE) aprobada. `motivo` es el iMotEmi (1 a 8, default 8 ajuste de precio;
   * ver `catalogs("note_motives")`).
   */
  debitNote<T = any>(
    cdc: string,
    items: SifenDebitNoteItem[],
    fields: { motivo?: number; reason?: string } = {},
    idempotencyKey?: string
  ): Promise<T> {
    return this.client.post<T>(`${BASE}/documents/${cdc}/debit-note/`, { items, ...compact(fields) }, idempotencyKey);
  }

  /** Inutiliza un rango (hasta 1000) de números nunca usados -- `POST /bill/sifen/inutilizaciones/`. */
  inutilizar<T = any>(
    fields: {
      tipo_de: number;
      establecimiento: string;
      punto_expedicion: string;
      desde: number;
      hasta: number;
      reason: string;
      serie?: string;
      timbrado?: string;
    },
    idempotencyKey?: string
  ): Promise<T> {
    return this.client.post<T>(`${BASE}/inutilizaciones/`, compact(fields), idempotencyKey);
  }

  // -- KuDE y compartir ---------------------------------------------------

  /** View-model del KuDE de un documento -- `GET /sales/sifen/documents/{cdc}/kude/`. */
  kude<T = any>(cdc: string): Promise<T> {
    return this.client.get<T>(`/sales/sifen/documents/${cdc}/kude/`);
  }

  /** KuDE de la factura vigente de una venta -- `GET /sales/{saleId}/sifen/kude/`. */
  saleKude<T = any>(saleId: string): Promise<T> {
    return this.client.get<T>(`/sales/${saleId}/sifen/kude/`);
  }

  /**
   * Envía el link del KuDE por email -- `POST /bill/sifen/documents/{cdc}/send-email/`.
   * `email` por defecto es el del cliente de la venta. Límite: 20 cada 5 minutos.
   */
  sendEmail<T = any>(cdc: string, email?: string): Promise<T> {
    return this.client.post<T>(`${BASE}/documents/${cdc}/send-email/`, compact({ email }));
  }

  /**
   * Crea un link público (sin login) del KuDE --
   * `POST /bill/sifen/documents/{cdc}/public-link/`. Vence entre 60 segundos y
   * 30 días (default 7 días).
   */
  publicLink<T = any>(cdc: string, expiresInSeconds?: number): Promise<T> {
    return this.client.post<T>(
      `${BASE}/documents/${cdc}/public-link/`,
      compact({ expires_in_seconds: expiresInSeconds })
    );
  }

  // -- ventas: emisión y notas de crédito ---------------------------------

  /**
   * Emite la factura de una venta ya creada -- `POST /sales/generate_invoice/{saleId}/`.
   * Es asíncrona, igual que `sales.create({ request_fiscal_document: true })`.
   */
  generateInvoice<T = any>(saleId: string): Promise<T> {
    return this.client.post<T>(`/sales/generate_invoice/${saleId}/`, {});
  }

  /**
   * Emite una nota de crédito electrónica (NCE) sobre una venta --
   * `POST /sales/{saleId}/credit_note/`. En SIFEN `lineas` es obligatorio: el
   * índice (desde 0) del renglón de la factura y la cantidad. Un renglón no se
   * acredita dos veces y la factura debe estar aprobada.
   */
  creditNote<T = any>(
    saleId: string,
    reason: string,
    lineas: SifenCreditNoteLine[],
    fields: { restore_stock?: boolean; update_current_account?: boolean } = {},
    idempotencyKey?: string
  ): Promise<T> {
    return this.client.post<T>(
      `/sales/${saleId}/credit_note/`,
      { reason, lineas, ...compact(fields) },
      idempotencyKey
    );
  }

  /** Calcula la nota de crédito sin emitirla -- `POST /sales/{saleId}/credit_note/preview/`. */
  creditNotePreview<T = any>(saleId: string, lineas: SifenCreditNoteLine[], reason?: string): Promise<T> {
    return this.client.post<T>(`/sales/${saleId}/credit_note/preview/`, { lineas, ...compact({ reason }) });
  }

  // -- receptor -----------------------------------------------------------

  /**
   * Registra un evento del receptor sobre un DE recibido --
   * `POST /received_invoices/sifen/events/`. `kind`: `notificacion`,
   * `conformidad`, `disconformidad` o `desconocimiento`. `fields` admite
   * `reason`, `total`, `emitted_at`, `received_at`, `total_gs` y `correction_of`.
   */
  receptorEvent<T = any>(kind: string, cdc: string, fields: Record<string, unknown> = {}): Promise<T> {
    return this.client.post<T>("/received_invoices/sifen/events/", { ...fields, kind, cdc });
  }

  // -- configuración y diagnóstico ----------------------------------------

  /** ¿Puedo emitir ahora? `can_invoice` + `blockers` + `warnings` -- `GET /bill/sifen/readiness/`. */
  readiness<T = any>(): Promise<T> {
    return this.client.get<T>(`${BASE}/readiness/`);
  }

  /**
   * Cambia el ambiente (`"test"` o `"prod"`) -- `POST /bill/sifen/environment/`.
   * Se rechaza con `ConflictError` si el ambiente destino no tiene certificado
   * y CSC válidos (`error_code`: `certificate_missing`, `csc_missing`, ...).
   */
  setEnvironment<T = any>(environment: "test" | "prod"): Promise<T> {
    return this.client.post<T>(`${BASE}/environment/`, { environment });
  }

  /** Estado (solo metadatos) del certificado y CSC -- `GET /bill/tax_info/taxpayer/sifen/certificates/[{env}/]`. */
  certificates<T = any>(environment?: "test" | "prod"): Promise<T> {
    return this.client.get<T>(`/bill/tax_info/taxpayer/sifen/certificates/${environment ? `${environment}/` : ""}`);
  }

  /**
   * Consulta un RUC en SIFEN (siConsRUC) -- `GET /bill/sifen/ruc/{ruc}/`.
   * Acepta `"80069563"` o `"80069563-1"`. Un DV errado se rechaza localmente.
   * Consultar el propio RUC sirve de prueba de certificado y conectividad.
   */
  ruc<T = any>(ruc: string): Promise<T> {
    return this.client.get<T>(`${BASE}/ruc/${ruc}/`);
  }

  /**
   * Prueba en vivo de conectividad con el certificado propio -- `POST /bill/sifen/diagnose/`.
   * Handshake mTLS + consulta del RUC emisor: `ok`, latencia de cada paso y `actions`.
   * Un fallo es un resultado (200), no un error. Límite: 10 por minuto.
   */
  diagnose<T = any>(): Promise<T> {
    return this.client.post<T>(`${BASE}/diagnose/`, {});
  }

  /**
   * ¿Esta caja puede emitir ahora? -- `POST /bill/sifen/verify-caja/`. Valida timbrado,
   * el par establecimiento/punto, el RUC del certificado y el estado del RUC emisor:
   * `valid` + `checks[]` (con `severity` y `action`) + `actions`.
   */
  verifyCaja<T = any>(fields: SifenVerifyCaja = {}): Promise<T> {
    return this.client.post<T>(`${BASE}/verify-caja/`, compact({ ...fields }));
  }

  /**
   * Consulta en vivo un lote enviado (siConsLoteDE) -- `GET /bill/sifen/lotes/{protocol}/`.
   * Solo lectura; 404 si el protocolo no es de este tenant. Límite: 30 por minuto.
   */
  lote<T = any>(protocol: string): Promise<T> {
    return this.client.get<T>(`${BASE}/lotes/${protocol}/`);
  }

  /** Tipos de documento (iTiDE) y cuáles emite la API, con su ruta -- `GET /bill/sifen/types/`. */
  types<T = any>(): Promise<T> {
    return this.client.get<T>(`${BASE}/types/`);
  }

  /**
   * ¿Se puede emitir `tipoDe`? -- `POST /bill/sifen/validate-type/`. `context` opcional:
   * `sale`, `standalone`, `credit_note` o `debit_note`. Responde `valid`, `issuable` y `reason`.
   */
  validateType<T = any>(tipoDe: number, context?: "sale" | "standalone" | "credit_note" | "debit_note"): Promise<T> {
    return this.client.post<T>(`${BASE}/validate-type/`, { tipo_de: tipoDe, ...compact({ context }) });
  }

  /** Último y próximo número de una secuencia -- `GET /bill/sifen/numbering/`. */
  numbering<T = any>(params: SifenNumberingParams = {}): Promise<T> {
    return this.client.get<T>(`${BASE}/numbering/`, params as Record<string, unknown>);
  }

  /** Continúa la numeración desde `lastUsed` (solo hacia arriba) -- `POST /bill/sifen/numbering/seed/`. */
  seedNumbering<T = any>(lastUsed: number, fields: SifenNumberingParams & { dry_run?: boolean } = {}): Promise<T> {
    return this.client.post<T>(`${BASE}/numbering/seed/`, { last_used: lastUsed, ...compact({ ...fields }) });
  }

  /** Catálogos de códigos (iTiDE, iMotEmi, IVA, pagos...) -- `GET /bill/sifen/catalogs/[{name}/]`. */
  catalogs<T = any>(name?: string): Promise<T> {
    return this.client.get<T>(name ? `${BASE}/catalogs/${name}/` : `${BASE}/catalogs/`);
  }
}
