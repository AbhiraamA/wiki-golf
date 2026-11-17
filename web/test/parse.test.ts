import { describe, expect, it } from 'vitest';
import { parseArticle } from '../src/lib/article/parse';
import type { Node } from '../src/lib/article/types';

const link = (title: string, label: string) =>
  `<a rel="mw:WikiLink" href="./${title}">${label}</a>`;

function text(nodes: Node[]): string {
  return nodes.map((n) => ('t' in n ? n.t : n.s)).join('');
}

const HTML = `
<section data-mw-section-id="0">
  <div class="shortdescription">Eight-limbed sea mollusc</div>
  <table class="infobox"><tr><td>${link('Cephalopod', 'Cephalopoda')}</td></tr></table>
  <p>An octopus is a ${link('Mollusca', 'mollusc')}<sup class="reference">[1]</sup> related to the ${link('Squid', 'squid')}.
     <span class="mw-editsection">edit</span></p>
  <figure><img src="x.jpg"><figcaption>${link('Caption_Link', 'caption')}</figcaption></figure>
  <p>It can <a rel="mw:WikiLink/Interwiki" href="./fr:poulpe">change</a> colour, see
     <a rel="mw:WikiLink" href="./File:Octopus.jpg">image</a> and ${link('Camouflage', 'camouflage')}.</p>
</section>
<section data-mw-section-id="1">
  <h2>Behaviour <span class="mw-editsection">[edit]</span></h2>
  <p>Octopuses are ${link('Intelligence', 'intelligent')}.</p>
</section>
<section><h2>References</h2><ol class="references"><li>a ref ${link('Hidden', 'hidden')}</li></ol></section>
<div class="navbox">${link('Nautilus', 'Nautilus')}</div>
`;

describe('parseArticle', () => {
  const m = parseArticle(HTML, 'Octopus');

  it('keeps the title and short description', () => {
    expect(m.title).toBe('Octopus');
    expect(m.description).toBe('Eight-limbed sea mollusc');
  });

  it('builds lead paragraphs from text and ns0 links only', () => {
    expect(m.lead.length).toBe(2);
    expect(text(m.lead[0]!)).toBe('An octopus is a mollusc related to the squid.');
    // Reference, edit link, interwiki and File: link are all dropped.
    expect(text(m.lead[1]!)).toBe('It can change colour, see image and camouflage.');
    const leadLinks = m.lead
      .flat()
      .filter((n): n is { l: string; s: string } => 'l' in n)
      .map((n) => n.l);
    expect(leadLinks).toEqual(['Mollusca', 'Squid', 'Camouflage']);
  });

  it('folds later sections and skips References', () => {
    expect(m.sections.map((s) => s.heading)).toEqual(['Behaviour']);
    expect(text(m.sections[0]!.paras[0]!)).toBe('Octopuses are intelligent.');
  });

  it('surfaces infobox and navbox links separately', () => {
    expect(m.quickFacts).toEqual(['Cephalopod']);
    expect(m.moreLinks).toEqual(['Nautilus']);
  });

  it('lists every playable link once, in reading order', () => {
    expect(m.allLinks).toEqual([
      'Mollusca',
      'Squid',
      'Camouflage',
      'Intelligence',
      'Cephalopod',
      'Nautilus',
    ]);
    expect(m.allLinks).not.toContain('Hidden');
    expect(m.allLinks).not.toContain('Caption_Link');
  });
});
