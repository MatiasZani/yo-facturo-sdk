/** Planes de suscripcion -- `/subscription-plans`. Scope: `recurring:read` / `recurring:write`. */

import type { YoFacturo } from "../client";
import { CrudResource } from "./base";

export class SubscriptionPlansResource extends CrudResource {
  constructor(client: YoFacturo) {
    super(client, "/subscription-plans");
  }
}
