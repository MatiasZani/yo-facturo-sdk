/** Alquileres -- `/rentals`. Scope: `rentals:read` / `rentals:write`. */

import type { YoFacturo } from "../client";
import { CrudResource, type ListParams } from "./base";

export interface RentalListParams extends ListParams {
  /**
   * Default `true`: sends `currency_aware=1`. Without it the API omits records whose
   * `price_currency` is not the account default currency (an old client would read them
   * as pesos). Each record in another currency carries `price_currency`; show it and
   * send it as `currency` when selling. Pass `false` to get only default-currency records.
   */
  currency_aware?: boolean;
}

export class RentalsResource extends CrudResource {
  constructor(client: YoFacturo) {
    super(client, "/rentals");
  }

  /** Lista paginada -- `GET /rentals/list/` (con `currency_aware=1` por defecto). */
  override list<T = any>(params: RentalListParams = {}): Promise<T> {
    const { currency_aware = true, ...rest } = params;
    return super.list<T>(currency_aware ? { ...rest, currency_aware: 1 } : rest);
  }
}
