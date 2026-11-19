/** Backup codes (plan.md §6): a 4-token code like `maple-fox-orbit-9` that moves a player's
 * progress to a new browser. Only the SHA-256 hash of the code is stored (players.backup_hash);
 * the plaintext is shown once, at creation, and never again. `restore` matches a code's hash to a
 * player and re-issues that player's cookie. No IP or other PII is stored (see the privacy page):
 * restore is throttled by a PII-free global per-minute attempt cap plus the code's own entropy. */

import type { Env } from '../env';

// Friendly, unambiguous words (no look-alikes). 128 words ^3 * 10 ≈ 21M combinations; with the
// restore throttle below, guessing a specific code is infeasible.
export const WORDS = [
  'acorn',
  'amber',
  'anchor',
  'apple',
  'arrow',
  'aspen',
  'badge',
  'bamboo',
  'basil',
  'beacon',
  'birch',
  'bison',
  'bloom',
  'branch',
  'breeze',
  'bronze',
  'brook',
  'cabin',
  'cactus',
  'cedar',
  'cherry',
  'clay',
  'clover',
  'cobalt',
  'comet',
  'coral',
  'cove',
  'crane',
  'crystal',
  'daisy',
  'dawn',
  'delta',
  'dune',
  'ember',
  'falcon',
  'fern',
  'fjord',
  'flint',
  'forest',
  'fox',
  'ginger',
  'glacier',
  'granite',
  'grove',
  'harbor',
  'hazel',
  'heron',
  'holly',
  'ivory',
  'jade',
  'juniper',
  'kelp',
  'lagoon',
  'lantern',
  'laurel',
  'lemon',
  'lily',
  'linen',
  'lotus',
  'lunar',
  'maple',
  'marble',
  'meadow',
  'mint',
  'mango',
  'moss',
  'nectar',
  'oak',
  'ocean',
  'olive',
  'onyx',
  'opal',
  'orbit',
  'otter',
  'pebble',
  'pine',
  'plum',
  'poppy',
  'prairie',
  'quartz',
  'quail',
  'raven',
  'reef',
  'river',
  'robin',
  'rowan',
  'ruby',
  'sage',
  'sand',
  'sequoia',
  'shell',
  'silver',
  'slate',
  'spruce',
  'star',
  'stone',
  'storm',
  'summit',
  'sunset',
  'swan',
  'teal',
  'thistle',
  'tide',
  'topaz',
  'trail',
  'tulip',
  'tundra',
  'umber',
  'valley',
  'vine',
  'violet',
  'walnut',
  'willow',
  'wren',
  'yarrow',
  'zephyr',
  'birdie',
  'bogey',
  'caddie',
  'course',
  'eagle',
  'fairway',
  'green',
  'links',
  'par',
  'putt',
  'tee',
  'wedge',
] as const;

const encoder = new TextEncoder();

export function generateCode(): string {
  const pick = () => WORDS[Math.floor(Math.random() * WORDS.length)];
  const digit = Math.floor(Math.random() * 10);
  return `${pick()}-${pick()}-${pick()}-${digit}`;
}

/** Lowercase, trim and collapse separators so a retyped code matches regardless of spacing/case. */
export function normalizeCode(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-');
}

export function isValidCodeFormat(code: string): boolean {
  return /^[a-z]+-[a-z]+-[a-z]+-\d$/.test(code);
}

export async function sha256Hex(s: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(s));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Create (or replace) the player's backup code; returns the plaintext to show once. Replacing
 * invalidates any previous code, since only one hash is stored per player.
 */
export async function createBackupCode(env: Env, playerId: string): Promise<string | null> {
  const code = generateCode();
  const hash = await sha256Hex(code);
  const res = await env.DB.prepare('UPDATE players SET backup_hash = ? WHERE id = ?')
    .bind(hash, playerId)
    .run();
  return res.meta.changes === 1 ? code : null;
}

export const RESTORE_MAX_PER_MINUTE = 30; // PII-free global brake; the code's entropy is the real lock

/** True if this restore attempt is within the global per-minute cap (and records it). */
export async function allowRestoreAttempt(env: Env, now: number): Promise<boolean> {
  const bucket = `restore:${Math.floor(now / 60_000)}`;
  const reset = (Math.floor(now / 60_000) + 1) * 60_000;
  await env.DB.prepare(
    `INSERT INTO rate_limits (bucket, count, reset_at) VALUES (?, 1, ?)
       ON CONFLICT(bucket) DO UPDATE SET count = count + 1`,
  )
    .bind(bucket, reset)
    .run();
  const row = await env.DB.prepare('SELECT count FROM rate_limits WHERE bucket = ?')
    .bind(bucket)
    .first<{ count: number }>();
  return (row?.count ?? 0) <= RESTORE_MAX_PER_MINUTE;
}

/** The player id whose backup code hashes to this one, or null if the code is unknown/malformed. */
export async function restoreByCode(env: Env, rawCode: string): Promise<string | null> {
  const code = normalizeCode(rawCode);
  if (!isValidCodeFormat(code)) return null;
  const hash = await sha256Hex(code);
  const row = await env.DB.prepare('SELECT id FROM players WHERE backup_hash = ?')
    .bind(hash)
    .first<{ id: string }>();
  return row?.id ?? null;
}
