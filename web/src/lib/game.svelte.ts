/** Client game state and flow (Svelte 5 runes). The server is the source of truth; this tracks
the current page, strokes and lie for rendering, and drives the screen transitions. */

import { isLongHole, localDate, weekday, type HoleInfo, type Lie } from '@wiki-golf/shared';
import { api, ApiError, type Me, type RoundResult } from './api';
import { parseArticle } from './article/parse';
import type { ArticleModel } from './article/types';
import { weekStart } from './dates';
import { allResults, savedResult, saveResult, toStored, type StoredResult } from './store';

export type TagKind = 'start' | 'dist' | Lie | 'mulligan' | 'caddie';
export type Screen = 'tee' | 'play' | 'holed';
export type View = 'home' | 'archive' | 'stats' | 'privacy';

const TAG_DELAY = 2200;

export class Game {
  date = localDate();
  screen = $state<Screen>('tee');
  view = $state<View>('home');
  loading = $state(true);
  error = $state<string | null>(null);

  hole = $state<HoleInfo | null>(null);
  me = $state<Me | null>(null);
  alreadyPlayed = $state(false); // ranked round for today already finished

  roundId = $state<string | null>(null);
  ranked = $state(true);
  practice = $state(false);

  article = $state<ArticleModel | null>(null);
  currentIdx = $state(0);
  currentRevId = $state(0);
  toPin = $state(0);
  maxDist = $state(1);
  strokes = $state(0); // score so far (shots + penalties)
  shotNo = $state(1); // next shot number
  shots = $state<{ lie: Lie; title: string }[]>([]);
  mulliganLeft = $state(true);
  hint = $state<string | null>(null);
  event = $state<TagKind | null>(null);
  lastLie = $state<Lie | null>(null);
  pageSeq = $state(0); // bumps on each new page, to re-key animations
  busy = $state(false);

  result = $state<RoundResult | null>(null);

  // toPin at each page we left, so a mulligan can restore it (the server never sends distances twice).
  #toPinStack: number[] = [];
  #tagTimer = 0;

  get eyebrow(): string {
    if (!this.hole) return '';
    const day = weekday(this.hole.date).toUpperCase();
    return `HOLE ${this.hole.holeNo} · ${day}${isLongHole(this.hole.date) ? ' LONG HOLE' : ''}`;
  }

  async init(): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      const [hole, me] = await Promise.all([api.hole(this.date), api.me().catch(() => null)]);
      this.hole = hole;
      this.me = me;
      this.maxDist = hole.par - 1;
      this.alreadyPlayed = savedResult(hole.date) !== null;
    } catch {
      this.error = 'Could not load today’s hole. Please try again.';
    } finally {
      this.loading = false;
    }
  }

  async teeOff(practice = false): Promise<void> {
    if (!this.hole || this.busy) return;
    this.busy = true;
    try {
      const r = await api.startRound(this.date);
      this.roundId = r.roundId;
      this.ranked = r.ranked;
      this.practice = practice || !r.ranked;
      this.article = parseArticle(r.html, r.page.title);
      this.currentIdx = r.page.idx;
      this.currentRevId = r.page.revId;
      this.toPin = this.maxDist;
      this.strokes = 0;
      this.shotNo = 1;
      this.shots = [];
      this.mulliganLeft = true;
      this.hint = null;
      this.lastLie = null;
      this.result = null;
      this.#toPinStack = [];
      this.pageSeq++;
      this.flash('start');
      this.screen = 'play';
    } catch {
      this.error = 'Could not start the round.';
    } finally {
      this.busy = false;
    }
  }

  flash(kind: TagKind): void {
    clearTimeout(this.#tagTimer);
    this.event = kind;
    this.#tagTimer = setTimeout(() => {
      this.event = null;
    }, TAG_DELAY) as unknown as number;
  }

  async playLink(title: string): Promise<void> {
    if (!this.roundId || this.busy || this.screen !== 'play') return;
    this.busy = true;
    this.hint = null;
    try {
      const out = await api.shot(this.roundId, {
        shotNo: this.shotNo,
        fromIdx: this.currentIdx,
        linkTitle: title,
      });
      this.shots = [...this.shots, { lie: out.lie, title: out.page.title }];
      this.shotNo++;
      this.strokes = out.strokes;
      this.#toPinStack.push(this.toPin);
      this.toPin = out.toPin;
      this.lastLie = out.lie;
      this.flash(out.lie);
      if (out.done) {
        await this.finish();
      } else if (out.html) {
        this.article = parseArticle(out.html, out.page.title);
        this.currentIdx = out.page.idx;
        this.currentRevId = out.page.revId;
        this.pageSeq++;
      }
    } catch {
      this.error = 'That move did not go through.';
    } finally {
      this.busy = false;
    }
  }

  async mulligan(): Promise<void> {
    if (!this.roundId || this.busy || !this.mulliganLeft || this.shots.length === 0) return;
    this.busy = true;
    try {
      const out = await api.mulligan(this.roundId);
      this.shots = this.shots.slice(0, -1);
      this.shotNo = Math.max(1, this.shotNo - 1);
      this.mulliganLeft = false;
      this.strokes = out.strokes;
      this.article = parseArticle(out.html, out.page.title);
      this.currentIdx = out.page.idx;
      this.currentRevId = out.page.revId;
      this.toPin = this.#toPinStack.pop() ?? this.maxDist;
      this.lastLie = null;
      this.hint = null;
      this.pageSeq++;
      this.flash('mulligan');
    } catch {
      this.error = 'Could not take the mulligan.';
    } finally {
      this.busy = false;
    }
  }

  async caddie(): Promise<void> {
    if (!this.roundId || this.busy || !this.article) return;
    this.busy = true;
    try {
      const out = await api.caddie(this.roundId, this.article.allLinks.slice(0, 40));
      this.hint = out.hint;
      this.strokes = out.strokes;
      this.flash('caddie');
      if (out.done) await this.finish();
    } catch {
      this.error = 'The caddie could not help.';
    } finally {
      this.busy = false;
    }
  }

  async finish(): Promise<void> {
    if (!this.roundId || !this.hole) return;
    clearTimeout(this.#tagTimer);
    this.event = null;
    const result = await api.result(this.roundId);
    this.result = result;
    if (!this.practice && this.ranked && result.done) {
      saveResult(toStored(this.hole.date, this.hole.holeNo, result));
      this.alreadyPlayed = true;
    }
    this.screen = 'holed';
  }

  seeResult(): void {
    if (!this.hole) return;
    const saved = savedResult(this.hole.date);
    if (!saved) return;
    this.practice = false;
    this.shots = saved.shots;
    this.result = {
      done: true,
      holed: saved.holed,
      word: saved.word,
      strokes: saved.strokes,
      par: saved.par,
      seconds: saved.seconds,
      ranked: saved.ranked,
      shots: saved.shots.map((s) => ({ toTitle: s.title, lie: s.lie })),
      rarity: 'pending',
    };
    this.screen = 'holed';
  }

  backToTee(): void {
    this.screen = 'tee';
    this.view = 'home';
    this.date = localDate();
    void this.init();
  }

  // ---- navigation (Archive / Stats / Privacy) -------------------------------

  openView(v: View): void {
    this.view = v;
  }

  closeView(): void {
    this.view = 'home';
  }

  /** Start a practice round on a past date from the Archive. Past dates are always practice. */
  async playDate(date: string): Promise<void> {
    this.view = 'home';
    this.date = date;
    await this.init();
    if (this.hole) await this.teeOff(true);
  }

  // ---- Stats data -----------------------------------------------------------

  /** Ranked finishes this week (Mon–Sun) and the average strokes over/under par, from local history. */
  stats(): { avgToPar: number | null; played: number; thisWeek: StoredResult[] } {
    const ranked = allResults().filter((r) => r.ranked && r.holed);
    const played = ranked.length;
    const avgToPar =
      played === 0 ? null : ranked.reduce((s, r) => s + (r.strokes - r.par), 0) / played;
    const monday = weekStart(localDate());
    const thisWeek = ranked
      .filter((r) => r.date >= monday)
      .sort((a, b) => a.date.localeCompare(b.date));
    return { avgToPar, played, thisWeek };
  }

  // ---- Backup code ----------------------------------------------------------

  async makeBackupCode(): Promise<string | null> {
    try {
      return (await api.backupCode()).code;
    } catch {
      return null;
    }
  }

  /** Restore progress from a backup code. Returns an error message, or null on success. */
  async restore(code: string): Promise<string | null> {
    const trimmed = code.trim();
    if (!trimmed) return 'Enter your backup code.';
    try {
      const me = await api.restore(trimmed);
      this.me = me;
      return null;
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) return 'Too many tries. Wait a minute.';
      return 'That code did not match. Check it and try again.';
    }
  }

  /** Dev/screenshot helper (mock only): drive the game to a screen. */
  async autoplay(target: 'play' | 'holed'): Promise<void> {
    await this.init();
    await this.teeOff(false);
    if (target === 'holed') {
      for (const t of ['Nautilus', 'Jules_Verne', 'Science_fiction', 'Moon', 'Apollo_11']) {
        await this.playLink(t);
      }
    }
  }
}
