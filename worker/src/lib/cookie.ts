/** Anonymous identity cookie `wg_pid = {uuid}.{hmac}`, signed with COOKIE_SECRET (plan.md §6). */

const COOKIE_NAME = 'wg_pid';
const MAX_AGE = 34_560_000; // 400 days

const encoder = new TextEncoder();

function b64url(bytes: ArrayBuffer): string {
  let s = '';
  for (const b of new Uint8Array(bytes)) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function key(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
}

async function sign(id: string, secret: string): Promise<string> {
  const mac = await crypto.subtle.sign('HMAC', await key(secret), encoder.encode(id));
  return b64url(mac);
}

/** Constant-time string compare. */
function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function makeCookieValue(id: string, secret: string): Promise<string> {
  return `${id}.${await sign(id, secret)}`;
}

/** The player id from a valid signed cookie, or null if absent or tampered. */
export async function readPlayerId(request: Request, secret: string): Promise<string | null> {
  const header = request.headers.get('Cookie');
  if (!header) return null;
  const match = header.match(/(?:^|;\s*)wg_pid=([^;]+)/);
  if (!match) return null;
  const value = decodeURIComponent(match[1] ?? '');
  const dot = value.lastIndexOf('.');
  if (dot <= 0) return null;
  const id = value.slice(0, dot);
  const mac = value.slice(dot + 1);
  if (!/^[0-9a-f-]{36}$/.test(id)) return null;
  return safeEqual(mac, await sign(id, secret)) ? id : null;
}

export async function setCookieHeader(id: string, secret: string): Promise<string> {
  const value = await makeCookieValue(id, secret);
  return `${COOKIE_NAME}=${value}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${MAX_AGE}`;
}

export function newPlayerId(): string {
  return crypto.randomUUID();
}
