/** Production safety guard: refuse to run if the cookie secret was never set to a real value.
 * The dev default lives in wrangler.jsonc `vars`; production overrides it with a `wrangler secret
 * put COOKIE_SECRET`. If that override is missing, cookies would be signed with a public key, so we
 * fail closed rather than issue forgeable identities. */

import type { Env } from '../env';

export const DEV_COOKIE_SECRET = 'dev-insecure-cookie-secret';

/** True when running as production but COOKIE_SECRET is absent or still the public dev default. */
export function productionCookieSecretMissing(env: Env): boolean {
  return (
    env.ENVIRONMENT === 'production' &&
    (!env.COOKIE_SECRET || env.COOKIE_SECRET === DEV_COOKIE_SECRET)
  );
}
