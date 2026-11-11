/** Productos -- `/products`. Scope: `products:read` / `products:write`. */

import type { YoFacturo } from "../client";
import { CrudResource, type ListParams } from "./base";

export interface ProductListParams extends ListParams {
  /**
   * Default `true`: sends `currency_aware=1`. Without it the API omits products whose
   * `price_currency` is not the account default currency (an old client would read them
   * as pesos). Each product in another currency carries `price_currency`; show it and
   * send it as `currency` when selling. Pass `false` to get only default-currency products.
   */
  currency_aware?: boolean;
}

export class ProductsResource extends CrudResource {
  constructor(client: YoFacturo) {
    super(client, "/products");
  }

  /** Lista paginada -- `GET /products/list/` (con `currency_aware=1` por defecto). */
  override list<T = any>(params: ProductListParams = {}): Promise<T> {
    const { currency_aware = true, ...rest } = params;
    return super.list<T>(currency_aware ? { ...rest, currency_aware: 1 } : rest);
  }
}
