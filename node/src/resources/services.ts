/** Servicios -- `/services`. Scope: `services:read` / `services:write`. */

import type { YoFacturo } from "../client";
import { CrudResource, type ListParams } from "./base";

export interface ServiceListParams extends ListParams {
  /**
   * Default `true`: sends `currency_aware=1`. Without it the API omits records whose
   * `price_currency` is not the account default currency (an old client would read them
   * as pesos). Each record in another currency carries `price_currency`; show it and
   * send it as `currency` when selling. Pass `false` to get only default-currency records.
   */
  currency_aware?: boolean;
}

export class ServicesResource extends CrudResource {
  constructor(client: YoFacturo) {
    super(client, "/services");
  }

  /** Lista paginada -- `GET /services/list/` (con `currency_aware=1` por defecto). */
  override list<T = any>(params: ServiceListParams = {}): Promise<T> {
    const { currency_aware = true, ...rest } = params;
    return super.list<T>(currency_aware ? { ...rest, currency_aware: 1 } : rest);
  }
}
