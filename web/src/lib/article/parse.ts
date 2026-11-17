/** Parse Parsoid HTML into a safe ArticleModel (plan.md §7). No HTML is ever injected back.

The input is parsed in an inert document (DOMParser), so no scripts run and no resources load.
We keep only namespace-0 wiki links and plain text; references, edit links, hatnotes, images,
infobox/navbox chrome and math are dropped (infobox/navbox links are surfaced separately).
*/

import type { ArticleModel, Node, Section } from './types';

// Link targets in these namespaces are not playable articles.
const NS_PREFIXES = new Set([
  'file',
  'image',
  'category',
  'template',
  'help',
  'portal',
  'wikipedia',
  'special',
  'media',
  'module',
  'draft',
  'talk',
]);

const DROP_SELECTOR = [
  'sup.reference',
  '.mw-references-wrap',
  'ol.references',
  '.reference',
  '.mw-editsection',
  '.hatnote',
  '.navigation-not-searchable',
  '.ambox',
  '.metadata',
  '.mbox-text',
  'figure',
  'img',
  '.thumb',
  '.gallery',
  '.mwe-math-element',
  'style',
  'script',
  'sup.noprint',
  '.noprint',
  '.mw-empty-elt',
  '.shortdescription',
].join(',');

function parseTitle(href: string): string | null {
  const raw = href.replace(/^\.\//, '').split('#')[0]?.split('?')[0] ?? '';
  let title: string;
  try {
    title = decodeURIComponent(raw);
  } catch {
    title = raw;
  }
  title = title.replace(/ /g, '_');
  if (!title) return null;
  const firstWord = title.split('_')[0] ?? '';
  const nsCandidate = firstWord.includes(':') ? firstWord.split(':')[0] : '';
  if (nsCandidate && NS_PREFIXES.has(nsCandidate.toLowerCase())) return null;
  return title;
}

function isWikiLink(el: Element): boolean {
  const rel = el.getAttribute('rel') ?? '';
  return rel.includes('mw:WikiLink') && !rel.includes('Interwiki');
}

/** Flatten an element's inline content into text/link nodes, coalescing adjacent text. */
function inlineNodes(el: Element, into: Node[] = []): Node[] {
  for (const child of Array.from(el.childNodes)) {
    if (child.nodeType === 3) {
      pushText(into, child.textContent ?? '');
    } else if (child.nodeType === 1) {
      const e = child as Element;
      if (e.tagName === 'A' && isWikiLink(e)) {
        const title = parseTitle(e.getAttribute('href') ?? '');
        const label = (e.textContent ?? '').trim();
        if (title && label) into.push({ l: title, s: label });
        else pushText(into, e.textContent ?? '');
      } else {
        inlineNodes(e, into);
      }
    }
  }
  return into;
}

function pushText(into: Node[], text: string): void {
  if (!text) return;
  const last = into[into.length - 1];
  if (last && 't' in last) last.t += text;
  else into.push({ t: text });
}

/** Collapse runs of whitespace in text nodes; drop empty paragraphs. */
function tidy(nodes: Node[]): Node[] {
  const out = nodes
    .map((n) => ('t' in n ? { t: n.t.replace(/\s+/g, ' ') } : n))
    .filter((n) => !('t' in n) || n.t !== '');
  if (out.length) {
    const first = out[0];
    if (first && 't' in first) first.t = first.t.replace(/^\s+/, '');
    const last = out[out.length - 1];
    if (last && 't' in last) last.t = last.t.replace(/\s+$/, '');
  }
  return out.filter((n) => !('t' in n) || n.t !== '');
}

function paragraphs(scope: Element): Node[][] {
  const out: Node[][] = [];
  for (const p of Array.from(scope.querySelectorAll(':scope > p'))) {
    const nodes = tidy(inlineNodes(p));
    if (nodes.some((n) => ('t' in n ? n.t.trim() : true))) out.push(nodes);
  }
  return out;
}

function linksIn(scope: Element): string[] {
  const out: string[] = [];
  for (const a of Array.from(scope.querySelectorAll('a'))) {
    if (!isWikiLink(a)) continue;
    const title = parseTitle(a.getAttribute('href') ?? '');
    if (title) out.push(title);
  }
  return out;
}

function dedupe(titles: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const t of titles) {
    if (!seen.has(t)) {
      seen.add(t);
      out.push(t);
    }
  }
  return out;
}

export function parseArticle(html: string, title: string): ArticleModel {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const root = doc.body;

  const description = doc.querySelector('.shortdescription')?.textContent?.trim() || null;

  // Pull infobox/navbox links out before dropping the chrome.
  const quickFacts = dedupe(
    Array.from(root.querySelectorAll('table.infobox, .infobox')).flatMap((t) => linksIn(t)),
  );
  const moreLinks = dedupe(
    Array.from(root.querySelectorAll('.navbox, .vertical-navbox, .sidebar')).flatMap((t) =>
      linksIn(t),
    ),
  );

  root
    .querySelectorAll('table.infobox, .infobox, .navbox, .vertical-navbox, .sidebar')
    .forEach((el) => el.remove());
  root.querySelectorAll(DROP_SELECTOR).forEach((el) => el.remove());

  // Sections: Parsoid wraps each in <section>. Section 0 (no heading) is the lead.
  const sectionEls = Array.from(root.querySelectorAll('section'));
  let lead: Node[][] = [];
  const sections: Section[] = [];
  if (sectionEls.length) {
    for (const sec of sectionEls) {
      const headingEl = sec.querySelector(':scope > h2, :scope > h3, :scope > h4');
      const paras = paragraphs(sec);
      if (!headingEl) {
        if (paras.length) lead.push(...paras);
      } else if (paras.length) {
        sections.push({ heading: (headingEl.textContent ?? '').trim(), paras });
      }
    }
  } else {
    lead = paragraphs(root);
  }

  const allLinks = dedupe([
    ...lead.flatMap((p) =>
      p.filter((n): n is { l: string; s: string } => 'l' in n).map((n) => n.l),
    ),
    ...sections.flatMap((s) =>
      s.paras.flatMap((p) =>
        p.filter((n): n is { l: string; s: string } => 'l' in n).map((n) => n.l),
      ),
    ),
    ...quickFacts,
    ...moreLinks,
  ]);

  return { title, description, lead, sections, quickFacts, moreLinks, allLinks };
}
