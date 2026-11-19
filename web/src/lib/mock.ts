/** In-memory mock backend for local dev and screenshots (VITE_MOCK=1). Not shipped to prod.

A small sample graph (Octopus → Apollo 11) with hand-written summaries, served as Parsoid-like
HTML so the real article parser and game flow exercise end to end without the Worker.
*/

import { pickUpAt, resultWord, type HoleInfo, type Lie } from '@wiki-golf/shared';
import type {
  Api,
  CaddieOutcome,
  MulliganOutcome,
  RoundResult,
  ShotOutcome,
  StartRound,
} from './api';

type Seg = { t: string } | { l: string; s: string };
interface Page {
  title: string;
  desc: string;
  dist: number;
  segs: Seg[];
}

const PAGES: Record<string, Page> = {
  octopus: {
    title: 'Octopus',
    desc: 'Eight-limbed sea mollusc',
    dist: 5,
    segs: [
      { t: 'An octopus is a soft-bodied, eight-limbed mollusc. Like its relatives the ' },
      { l: 'squid', s: 'squid' },
      { t: ' and the ' },
      { l: 'nautilus', s: 'nautilus' },
      { t: ', it belongs to the ' },
      { l: 'cephalopod', s: 'cephalopods' },
      { t: '. Octopuses are known for their intelligence and for ' },
      { l: 'camouflage', s: 'camouflage' },
      { t: ', changing colour and texture in a fraction of a second.' },
    ],
  },
  cephalopod: {
    title: 'Cephalopod',
    desc: 'Class of molluscs',
    dist: 5,
    segs: [
      {
        t: 'Cephalopods are molluscs with arms or tentacles around the head. The group includes the ',
      },
      { l: 'octopus', s: 'octopus' },
      { t: ', the ' },
      { l: 'squid', s: 'squid' },
      { t: ' and the shelled ' },
      { l: 'nautilus', s: 'nautilus' },
      { t: '. Many can change colour in an instant.' },
    ],
  },
  squid: {
    title: 'Squid',
    desc: 'Long-bodied cephalopods',
    dist: 6,
    segs: [
      { t: 'Squid have long bodies, eight arms and two longer tentacles. The ' },
      { l: 'giantsquid', s: 'giant squid' },
      { t: ' can reach about 12 metres. Like other ' },
      { l: 'cephalopod', s: 'cephalopods' },
      { t: ', they squirt ink to escape.' },
    ],
  },
  nautilus: {
    title: 'Nautilus',
    desc: 'Shelled cephalopod',
    dist: 4,
    segs: [
      { t: 'The nautilus is a ' },
      { l: 'cephalopod', s: 'cephalopod' },
      { t: ' that lives in a coiled, chambered shell. Its name was given to the submarine in ' },
      { l: 'leagues', s: 'Twenty Thousand Leagues Under the Seas' },
      { t: ', the novel by ' },
      { l: 'verne', s: 'Jules Verne' },
      { t: '.' },
    ],
  },
  camouflage: {
    title: 'Camouflage',
    desc: 'Hiding by blending in',
    dist: 6,
    segs: [
      { t: 'Camouflage is the use of colour and pattern to stay hidden. The ' },
      { l: 'octopus', s: 'octopus' },
      { t: ' and other ' },
      { l: 'cephalopod', s: 'cephalopods' },
      { t: ' can change theirs in an instant.' },
    ],
  },
  giantsquid: {
    title: 'Giant squid',
    desc: 'Deep-ocean squid',
    dist: 5,
    segs: [
      { t: 'The giant squid is a deep-ocean ' },
      { l: 'squid', s: 'squid' },
      { t: ' with some of the largest eyes of any animal. One attacks the submarine in ' },
      { l: 'leagues', s: 'Twenty Thousand Leagues Under the Seas' },
      { t: '.' },
    ],
  },
  leagues: {
    title: 'Twenty Thousand Leagues Under the Seas',
    desc: '1870 novel by Jules Verne',
    dist: 4,
    segs: [
      { t: 'An adventure novel by ' },
      { l: 'verne', s: 'Jules Verne' },
      { t: '. Aboard the submarine Nautilus, the crew survive storms, ice and a ' },
      { l: 'giantsquid', s: 'giant squid' },
      { t: '.' },
    ],
  },
  verne: {
    title: 'Jules Verne',
    desc: 'French novelist, 1828–1905',
    dist: 3,
    segs: [
      { t: 'Jules Verne wrote adventure stories far ahead of his time, including ' },
      { l: 'leagues', s: 'Twenty Thousand Leagues Under the Seas' },
      { t: ' and ' },
      { l: 'earthmoon', s: 'From the Earth to the Moon' },
      { t: '. He is called a father of ' },
      { l: 'scifi', s: 'science fiction' },
      { t: '.' },
    ],
  },
  scifi: {
    title: 'Science fiction',
    desc: 'Genre of speculative fiction',
    dist: 2,
    segs: [
      { t: 'Science fiction imagines worlds shaped by technology. Early writers such as ' },
      { l: 'verne', s: 'Jules Verne' },
      { t: ' imagined voyages to the ' },
      { l: 'moon', s: 'Moon' },
      { t: ' long before anyone went.' },
    ],
  },
  earthmoon: {
    title: 'From the Earth to the Moon',
    desc: '1865 novel by Jules Verne',
    dist: 2,
    segs: [
      { t: 'In this novel by ' },
      { l: 'verne', s: 'Jules Verne' },
      { t: ', a gun club builds a cannon to fire a crewed projectile at the ' },
      { l: 'moon', s: 'Moon' },
      { t: '.' },
    ],
  },
  moon: {
    title: 'Moon',
    desc: 'Earth’s natural satellite',
    dist: 1,
    segs: [
      { t: 'The Moon is Earth’s only natural satellite. People first walked on it during ' },
      { l: 'apollo', s: 'Apollo 11' },
      { t: ' in 1969, long imagined in ' },
      { l: 'scifi', s: 'science fiction' },
      { t: '.' },
    ],
  },
  apollo: {
    title: 'Apollo 11',
    desc: 'First crewed Moon landing, 1969',
    dist: 0,
    segs: [{ t: 'Apollo 11 was the 1969 mission that first landed people on the Moon.' }],
  },
};

const KEYS = Object.keys(PAGES);
const idxOf = (key: string) => KEYS.indexOf(key);
const byTitle = (title: string): string =>
  KEYS.find((k) => PAGES[k]!.title.replace(/ /g, '_') === title.replace(/ /g, '_')) ?? '';

const PAR = 6;
const PICKUP = pickUpAt(PAR);

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function pageHtml(key: string): string {
  const page = PAGES[key]!;
  const inner = page.segs
    .map((g) =>
      'l' in g
        ? `<a rel="mw:WikiLink" href="./${esc(PAGES[g.l]!.title.replace(/ /g, '_'))}">${esc(g.s)}</a>`
        : esc(g.t),
    )
    .join('');
  return `<section data-mw-section-id="0"><div class="shortdescription">${esc(page.desc)}</div><p>${inner}</p></section>`;
}

function ref(key: string) {
  return {
    idx: idxOf(key),
    title: PAGES[key]!.title.replace(/ /g, '_'),
    revId: 1000 + idxOf(key),
    shortDesc: PAGES[key]!.desc,
  };
}

function lie(from: number, to: number): Lie {
  if (to === 0) return 'holed';
  if (to < from) return 'fairway';
  if (to === from) return 'rough';
  return 'bunker';
}

interface MockRound {
  page: string;
  shots: { key: string; lie: Lie }[];
  penalties: number;
  mulligan: boolean;
  t0: number;
  done: boolean;
  result: 'holed' | 'pickup' | null;
}

const rounds = new Map<string, MockRound>();
const strokesOf = (r: MockRound) => r.shots.length + r.penalties;
const delay = <T>(v: T) => new Promise<T>((res) => setTimeout(() => res(v), 120));

const HOLE: HoleInfo = {
  holeNo: 128,
  date: '',
  wiki: 'simplewiki',
  par: PAR,
  pickUp: PICKUP,
  start: ref('octopus'),
  target: ref('apollo'),
};

export const mockApi: Api = {
  async hole(date) {
    return delay({ ...HOLE, date });
  },
  async page(title, _date) {
    const key = byTitle(title) || 'octopus';
    return delay({ ...ref(key), html: pageHtml(key) });
  },
  async startRound(date): Promise<StartRound> {
    const id = crypto.randomUUID();
    rounds.set(id, {
      page: 'octopus',
      shots: [],
      penalties: 0,
      mulligan: false,
      t0: 0,
      done: false,
      result: null,
    });
    return delay({
      roundId: id,
      ranked: true,
      hole: { ...HOLE, date },
      page: ref('octopus'),
      html: pageHtml('octopus'),
    });
  },
  async shot(roundId, body): Promise<ShotOutcome> {
    const r = rounds.get(roundId)!;
    const key = byTitle(body.linkTitle);
    const from = PAGES[r.page]!.dist;
    const to = PAGES[key]!.dist;
    const l = lie(from, to);
    r.shots.push({ key, lie: l });
    r.page = key;
    r.t0 ||= Date.now();
    const holed = l === 'holed';
    const done = holed || strokesOf(r) >= PICKUP;
    if (done) {
      r.done = true;
      r.result = holed ? 'holed' : 'pickup';
    }
    return delay({
      lie: l,
      strokes: strokesOf(r),
      toPin: to,
      holed,
      done,
      page: ref(key),
      html: holed ? null : pageHtml(key),
    });
  },
  async mulligan(roundId): Promise<MulliganOutcome> {
    const r = rounds.get(roundId)!;
    r.shots.pop();
    r.mulligan = true;
    r.page = r.shots.length ? r.shots[r.shots.length - 1]!.key : 'octopus';
    return delay({ page: ref(r.page), html: pageHtml(r.page), strokes: strokesOf(r) });
  },
  async caddie(roundId, linkTitles): Promise<CaddieOutcome> {
    const r = rounds.get(roundId)!;
    const from = PAGES[r.page]!.dist;
    const hint = linkTitles.find((t) => {
      const k = byTitle(t);
      return k && PAGES[k]!.dist < from;
    });
    r.penalties += 1;
    r.t0 ||= Date.now();
    const done = strokesOf(r) >= PICKUP;
    if (done) {
      r.done = true;
      r.result = 'pickup';
    }
    return delay({ hint: hint ?? null, strokes: strokesOf(r), done });
  },
  async result(roundId): Promise<RoundResult> {
    const r = rounds.get(roundId);
    if (!r || !r.done) return delay({ done: false });
    const holed = r.result === 'holed';
    const secs = Math.max(0, Math.round((Date.now() - (r.t0 || Date.now())) / 1000));
    return delay({
      done: true,
      holed,
      word: resultWord(holed, strokesOf(r), PAR),
      strokes: strokesOf(r),
      par: PAR,
      seconds: secs,
      ranked: true,
      shots: r.shots.map((s) => ({ toTitle: PAGES[s.key]!.title.replace(/ /g, '_'), lie: s.lie })),
      rarity: 'pending',
    });
  },
  async me() {
    return delay({ streakCurrent: 9, streakBest: 14, gamesPlayed: 42, lastDate: null });
  },
};
