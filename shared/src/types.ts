/** Types shared by the web app and the Worker. */

import type { Wiki } from './config';

export type Lie = 'fairway' | 'rough' | 'bunker' | 'holed' | 'out_of_bounds';

export interface PageRef {
  idx: number;
  title: string;
  revId: number;
}

/** Shown on the tee screen for a themed day (holiday, anniversary). */
export interface Badge {
  label: string;
  emoji: string;
}

/** Public hole info returned by `GET /api/hole`. Never includes distances. */
export interface HoleInfo {
  holeNo: number;
  date: string;
  wiki: Wiki;
  par: number;
  pickUp: number;
  start: PageRef;
  target: PageRef;
  /** Present only on themed days. */
  badge?: Badge;
}
