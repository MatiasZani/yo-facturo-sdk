/** Productos -- `/products`. Scope: `products:read` / `products:write`. */

import type { YoFacturo } from "../client";
import { CrudResource } from "./base";

export class ProductsResource extends CrudResource {
  constructor(client: YoFacturo) {
    super(client, "/products");
  }
}
