/** Ventas -- `/sales`. Scope: `sales:read` / `sales:write`. */

import type { YoFacturo } from "../client";
import { CrudResource } from "./base";

export class SalesResource extends CrudResource {
  constructor(client: YoFacturo) {
    super(client, "/sales");
  }
}
