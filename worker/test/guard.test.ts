import { describe, expect, it } from 'vitest';
import { DEV_COOKIE_SECRET, productionCookieSecretMissing } from '../src/lib/guard';
import type { Env } from '../src/env';

function env(partial: Partial<Env>): Env {
  return { ENVIRONMENT: 'production', COOKIE_SECRET: 'x', ...partial } as Env;
}

describe('productionCookieSecretMissing', () => {
  it('blocks production with no secret or the dev default', () => {
    expect(productionCookieSecretMissing(env({ COOKIE_SECRET: '' }))).toBe(true);
    expect(productionCookieSecretMissing(env({ COOKIE_SECRET: DEV_COOKIE_SECRET }))).toBe(true);
  });

  it('allows production with a real secret', () => {
    expect(
      productionCookieSecretMissing(env({ COOKIE_SECRET: 'a-long-random-production-value' })),
    ).toBe(false);
  });

  it('never blocks dev, whatever the secret', () => {
    expect(productionCookieSecretMissing(env({ ENVIRONMENT: 'dev', COOKIE_SECRET: '' }))).toBe(
      false,
    );
    expect(
      productionCookieSecretMissing(env({ ENVIRONMENT: 'dev', COOKIE_SECRET: DEV_COOKIE_SECRET })),
    ).toBe(false);
  });
});
