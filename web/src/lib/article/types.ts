/** Safe article model built from Parsoid HTML. Rendered with Svelte nodes only — never innerHTML. */

/** One inline run: plain text, or a playable wiki link (title + visible label). */
export type Node = { t: string } | { l: string; s: string };

export interface Section {
  heading: string;
  paras: Node[][];
}

export interface ArticleModel {
  title: string;
  description: string | null;
  lead: Node[][];
  sections: Section[];
  quickFacts: string[]; // infobox link titles (folded "Quick facts")
  moreLinks: string[]; // navbox/table link titles (folded "More links")
  allLinks: string[]; // every playable link title on the page, reading order, deduped
}
