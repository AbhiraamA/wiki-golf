-- Wiki Golf initial schema (plan.md section 4).

CREATE TABLE players (
  id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  streak_current INTEGER NOT NULL DEFAULT 0,
  streak_best INTEGER NOT NULL DEFAULT 0,
  last_date TEXT,
  games_played INTEGER NOT NULL DEFAULT 0,
  backup_hash TEXT
);

CREATE TABLE rounds (
  id TEXT PRIMARY KEY,
  player_id TEXT NOT NULL,
  hole_date TEXT NOT NULL,
  ranked INTEGER NOT NULL,
  started_at INTEGER NOT NULL,
  first_shot_at INTEGER,
  finished_at INTEGER,
  current_idx INTEGER NOT NULL,
  current_title TEXT NOT NULL,
  strokes INTEGER NOT NULL DEFAULT 0,
  penalties INTEGER NOT NULL DEFAULT 0,
  mulligan_used INTEGER NOT NULL DEFAULT 0,
  result TEXT,
  rarity INTEGER
);
CREATE UNIQUE INDEX rounds_one_ranked ON rounds (player_id, hole_date) WHERE ranked = 1;
CREATE INDEX rounds_by_date ON rounds (hole_date, finished_at);
CREATE INDEX rounds_by_player ON rounds (player_id, started_at);

CREATE TABLE shots (
  round_id TEXT NOT NULL,
  shot_no INTEGER NOT NULL,
  from_idx INTEGER NOT NULL,
  to_idx INTEGER NOT NULL,
  to_title TEXT NOT NULL,
  lie TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (round_id, shot_no)
);

CREATE TABLE page_visits (
  hole_date TEXT NOT NULL,
  page_idx INTEGER NOT NULL,
  finishers INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (hole_date, page_idx)
);

CREATE TABLE hole_stats (
  hole_date TEXT PRIMARY KEY,
  finishers INTEGER NOT NULL,
  score_spread TEXT NOT NULL,
  top_route TEXT,
  updated_at INTEGER NOT NULL
);
