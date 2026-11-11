/** Turnos -- `/appointments`. Scope: `appointments:read` / `appointments:write`. */

import type { YoFacturo } from "../client";
import { CrudResource } from "./base";

export class AppointmentsResource extends CrudResource {
  constructor(client: YoFacturo) {
    super(client, "/appointments");
  }
}
