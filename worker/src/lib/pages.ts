/** Pinned-revision article HTML: served from R2, or fetched from Wikimedia and cached there.

The Worker never injects this HTML anywhere; it returns it to the client, which parses it in an
inert document. Here it is used only to list the page's outgoing links for shot validation.
*/

import { USER_AGENT, WIKIS, type Wiki } from '@wiki-golf/shared';
import type { Env } from '../env';

const ANCHOR_RE = /<a\s[^>]*>/gi;
const HREF_RE = /href="\.\/([^"#?]+)/;

/** Underscored titles of namespace-0 wiki links in Parsoid HTML (document order). */
export function linkTitles(html: string): string[] {
  const out: string[] = [];
  const anchors = html.match(ANCHOR_RE);
  if (!anchors) return out;
  for (const tag of anchors) {
    if (!tag.includes('mw:WikiLink') || tag.includes('mw:WikiLink/Interwiki')) continue;
    const m = tag.match(HREF_RE);
    if (!m) continue;
    let title: string;
    try {
      title = decodeURIComponent(m[1] ?? '');
    } catch {
      title = m[1] ?? '';
    }
    title = title.replace(/ /g, '_');
    if (title) out.push(title);
  }
  return out;
}

function revUrl(wiki: Wiki, revId: number): string {
  const lang = WIKIS[wiki].lang;
  return `https://${lang}.wikipedia.org/w/rest.php/v1/revision/${revId}/html`;
}

/** HTML for a pinned revision, from R2 or (on a miss) Wikimedia REST, then cached to R2. */
export async function getRevisionHtml(env: Env, revId: number): Promise<string | null> {
  const key = `html/${env.WIKI}/${revId}.html`;
  const cached = await env.BUCKET.get(key);
  if (cached) return cached.text();

  const resp = await fetch(revUrl(env.WIKI, revId), {
    headers: { 'User-Agent': USER_AGENT, Accept: 'text/html' },
    cf: { cacheTtl: 0 },
  });
  if (!resp.ok) return null;
  const html = await resp.text();
  await env.BUCKET.put(key, html, { httpMetadata: { contentType: 'text/html; charset=utf-8' } });
  return html;
}
