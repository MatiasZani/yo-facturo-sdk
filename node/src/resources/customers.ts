/** Clientes -- `/customers`. Scope: `customers:read` / `customers:write`. */

import type { YoFacturo } from "../client";
import { CrudResource } from "./base";

export class CustomersResource extends CrudResource {
  constructor(client: YoFacturo) {
    super(client, "/customers");
  }
}
