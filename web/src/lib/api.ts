/** Typed client for the Worker API (plan.md §6). In dev with VITE_MOCK it uses an in-memory mock. */

import type { HoleInfo, Lie, PageRef } from '@wiki-golf/shared';

export interface PageContent extends PageRef {
  html: string;
}

export interface StartRound {
  roundId: string;
  ranked: boolean;
  hole: HoleInfo;
  page: PageRef;
  html: string;
}

export interface ShotOutcome {
  lie: Lie;
  strokes: number;
  toPin: number;
  holed: boolean;
  done: boolean;
  page: PageRef;
  html: string | null;
}

export interface MulliganOutcome {
  page: PageRef;
  html: string;
  strokes: number;
}

export interface CaddieOutcome {
  hint: string | null;
  strokes: number;
  done: boolean;
}

export interface RoundResult {
  done: boolean;
  holed?: boolean;
  word?: string;
  strokes?: number;
  par?: number;
  seconds?: number;
  ranked?: boolean;
  shots?: { toTitle: string; lie: Lie }[];
  rarity?: number | 'pending';
}

export interface Me {
  streakCurrent: number;
  streakBest: number;
  gamesPlayed: number;
  lastDate: string | null;
}

export interface Restored extends Me {
  restored: boolean;
}

export interface Api {
  hole(date: string): Promise<HoleInfo>;
  page(title: string, date: string): Promise<PageContent>;
  startRound(date: string): Promise<StartRound>;
  shot(
    roundId: string,
    body: { shotNo: number; fromIdx: number; linkTitle: string },
  ): Promise<ShotOutcome>;
  mulligan(roundId: string): Promise<MulliganOutcome>;
  caddie(roundId: string, linkTitles: string[]): Promise<CaddieOutcome>;
  result(roundId: string): Promise<RoundResult>;
  me(): Promise<Me>;
  backupCode(): Promise<{ code: string }>;
  restore(code: string): Promise<Restored>;
}

export class ApiError extends Error {
  constructor(
    public code: string,
    public status: number,
  ) {
    super(code);
  }
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    credentials: 'include',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = (await res.json().catch(() => ({}))) as T & { error?: string };
  if (!res.ok) throw new ApiError(data.error ?? 'request_failed', res.status);
  return data;
}

const liveApi: Api = {
  hole: (date) => call('GET', `/hole?date=${date}`),
  page: (title, date) => call('GET', `/page?title=${encodeURIComponent(title)}&date=${date}`),
  startRound: (date) => call('POST', '/rounds', { date }),
  shot: (id, body) => call('POST', `/rounds/${id}/shots`, body),
  mulligan: (id) => call('POST', `/rounds/${id}/mulligan`, {}),
  caddie: (id, linkTitles) => call('POST', `/rounds/${id}/caddie`, { linkTitles }),
  result: (id) => call('GET', `/rounds/${id}/result`),
  me: () => call('GET', '/me'),
  backupCode: () => call('POST', '/backup-code', {}),
  restore: (code) => call('POST', '/restore', { code }),
};

// Vite statically replaces import.meta.env.VITE_MOCK; the mock is tree-shaken out of prod builds.
export const api: Api = import.meta.env.VITE_MOCK ? (await import('./mock')).mockApi : liveApi;
