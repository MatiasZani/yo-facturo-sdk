/** Mixin con el patrón CRUD estándar de la API (ver /dev/conventions/). */

import type { YoFacturo } from "../client";

export interface ListParams {
  page?: number;
  per_page?: number;
  search?: string;
  sort?: string;
  sort_dir?: 1 | -1;
  fields?: string;
  [key: string]: unknown;
}

export class CrudResource {
  protected readonly client: YoFacturo;
  protected readonly base: string;

  constructor(client: YoFacturo, base: string) {
    this.client = client;
    this.base = base;
  }

  /** Lista paginada -- `GET {base}/list/`. */
  list<T = any>(params: ListParams = {}): Promise<T> {
    return this.client.get<T>(`${this.base}/list/`, params);
  }

  /** Un registro por su id -- `GET {base}/{id}/`. */
  get<T = any>(id: string): Promise<T> {
    return this.client.get<T>(`${this.base}/${id}/`);
  }

  /** Crea un registro -- `POST {base}/`. `idempotencyKey` es opcional. */
  create<T = any>(fields: Record<string, unknown> = {}, idempotencyKey?: string): Promise<T> {
    return this.client.post<T>(`${this.base}/`, fields, idempotencyKey);
  }

  /**
   * Actualiza los campos enviados -- `PUT {base}/{id}/`. Los campos
   * omitidos se mantienen sin cambios; para borrar el valor de un campo
   * mandá `null` explícito.
   */
  update<T = any>(id: string, fields: Record<string, unknown> = {}): Promise<T> {
    return this.client.put<T>(`${this.base}/${id}/`, fields);
  }

  /** Elimina (baja lógica) -- `DELETE {base}/{id}/`. */
  delete<T = any>(id: string): Promise<T> {
    return this.client.delete<T>(`${this.base}/${id}/`);
  }
}
