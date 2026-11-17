# Wiki Golf — Build Plan

This file is the brief for the coding agent. Read it fully before writing code, then work phase by phase. Keep a running checklist in `PROGRESS.md` and tick items off as they land.

## 1. What we are building

Wiki Golf is a free daily web game. Every player gets the same start and target Wikipedia article each day. Each tap on a link inside the article is one stroke. The goal is to reach the target in as few strokes as possible, scored against par like golf.

- Web only: it must work in desktop browsers and mobile browsers. No native apps, no app-store builds, no install prompts.
- Must run on free tiers: Cloudflare Workers Free, D1 free, R2 free, GitHub Actions on a public repo. Never add a paid resource without asking the owner.
- The UI reference is `design/mock.html` (open it in a browser). Match its look, layout, copy and behaviour. It is a throwaway prototype: rebuild it properly, don't copy its code wholesale.

### Game rules (source of truth)

| Term | Rule |
| --- | --- |
| Hole | A start article and a target article for one calendar date. Same for everyone. |
| Stroke | One tap on a link in the current article. |
| Par | Shortest route in clicks + 1. |
| Pick-up | At double par the round ends with a score of double par. |
| Fairway | The new page is closer to the target than the previous page. |
| Rough | The new page is the same distance from the target. |
| Bunker | The new page is farther from the target. |
| Holed | The new page is the target. |
| Out of bounds | The new page has no route to the target (distance 255). |
| Mulligan | Undo the last shot once per round; that stroke is given back. |
| Caddie | Highlights one link on the current page that gets closer. Costs 1 penalty stroke. |
| Find a link | Search the links on the current page. Free. |
| Time | First stroke to finish, measured by the server. Shown on the scorecard. Used only to break ties. |
| Rarity | 0 to 100: how uncommon a finisher's route was among that day's finishers. |
| Ranked round | The first round a player starts for a date. Later rounds on that date, and any round on a past date, are practice: no effect on streaks, rarity or rankings. |

Difficulty schedule (par is drawn at random within the range, seeded by the date):

| Day | Par range |
| --- | --- |
| Mon–Tue | 3–4 |
| Wed–Thu | 4–5 |
| Fri–Sat | 4–6 |
| Sun | 6–7 ("long hole") |

Hole number = days since `HOLE_EPOCH` + 1. `HOLE_EPOCH` is the launch date, set in shared config.

## 2. Locked decisions

| Area | Decision |
| --- | --- |
| Name | Wiki Golf |
| Repo | Public GitHub repo `wiki-golf` |
| Front end | Svelte 5 + Vite + TypeScript, built as a single-page app |
| Server | One Cloudflare Worker (TypeScript, Hono) serving the API under `/api/*` and the built front end as Workers Static Assets with SPA fallback |
| Database | Cloudflare D1 (SQLite) for players, rounds, shots and stats |
| Files | Cloudflare R2 bucket `wiki-golf` for snapshots, title index shards, hole files, distance files and cached article HTML |
| Hole builder | Python 3.12 package in `builder/`, run only in GitHub Actions |
| Dev data | Simple English Wikipedia (`simplewiki`) until Phase 6; English Wikipedia (`enwiki`) for launch |
| Contact | `wikigolf23@gmail.com` (goes in the User-Agent; this repo is public, so it will be visible) |
| Identity | Anonymous random player ID in a signed cookie. No names, emails, passwords or IP addresses stored. |

### Hard rules for the agent

1. Never run the hole builder against full English Wikipedia on the owner's computer. Builds run in GitHub Actions. Unit tests use tiny fixture files.
2. Never put Wikipedia HTML into the page with `innerHTML` or Svelte `{@html}`. Parse it, extract text and links, and render those as plain nodes.
3. Never commit secrets. Use GitHub Actions secrets and `wrangler secret put`.
4. Every request to Wikimedia sends `User-Agent: WikiGolf/<version> (https://github.com/<owner>/wiki-golf; wikigolf23@gmail.com)`. Download dumps one file at a time on a single connection. Back off and retry on HTTP 429 and 5xx.
5. Stay inside free-tier budgets (section 9). If a feature would break them, stop and write the trade-off in `PROGRESS.md` instead of building it.
6. Ask the owner before: creating any paid resource, adding a domain, changing repo visibility, or deleting data in R2 or D1.

## 3. Repo layout

```
wiki-golf/
├─ plan.md                 this file
├─ PROGRESS.md             running checklist the agent maintains
├─ design/mock.html        UI reference (not shipped)
├─ package.json            npm workspaces: web, worker, shared
├─ shared/                 TypeScript used by web and worker
│  └─ src/                 rules.ts (par, lies, pick-up), schedule.ts, types.ts, config.ts
├─ web/                    Svelte 5 + Vite app, builds to web/dist
│  └─ src/
│     ├─ lib/article/      Parsoid HTML → safe article model
│     ├─ lib/api.ts        typed API client
│     ├─ lib/store.ts      local history and settings
│     ├─ components/       CourseBar, ArticleCard, Dock, FindSheet, BagSheet, SidePanel, ...
│     └─ screens/          Tee, Play, Holed, Archive, Stats, HowToPlay, Privacy
├─ worker/
│  ├─ src/index.ts         Hono app; API routes; scheduled() handler
│  ├─ src/lib/             cookie.ts, titles.ts, distances.ts, pages.ts, rounds.ts, rarity.ts
│  ├─ migrations/          D1 SQL migrations
│  ├─ test/                vitest + @cloudflare/vitest-pool-workers
│  └─ wrangler.jsonc
├─ builder/
│  ├─ pyproject.toml
│  ├─ wikigolf_builder/    dumps.py, sqlparse.py, graph.py, bfs.py, pick.py, verify.py, export.py, upload.py, cli.py
│  └─ tests/               fixtures with a hand-made 20-page wiki
└─ .github/workflows/      ci.yml, deploy.yml, build-holes.yml
```

## 4. Data and files

### R2 layout (bucket `wiki-golf`)

| Key | Contents |
| --- | --- |
| `snapshots/{snap}/meta.json` | `{ snap, wiki, dumpDate, articleCount, linkCount, shardCount, builtAt }`. `snap` = `{wiki}-{dumpDate}`, e.g. `simplewiki-20261101`. |
| `snapshots/{snap}/titles/{shard}.json` | Title index shard: `{ "Title_With_Underscores": [pageIdx, revId] }`. Redirect titles map to their target's entry. Shard = FNV-1a 32-bit hash of the title modulo `shardCount` (1024 for enwiki, 64 for simplewiki). |
| `snapshots/{snap}/pages/{pageIdx}.json` | `{ title, revId }` for each page index, sharded the same way if one file per page is too many (decide in Phase 1 and record it here). |
| `holes/{YYYY-MM-DD}.json` | `{ holeNo, date, snap, wiki, par, pickUp, shortest, start: {idx, title, revId}, target: {idx, title, revId}, difficulty, status }` |
| `holes/index.json` | List of available dates with hole numbers and status. |
| `distances/{YYYY-MM-DD}.bin` | `Uint8Array` of length `articleCount`: clicks from each page index to the target. 255 = no route. |
| `html/{wiki}/{revId}.html` | Cached Parsoid HTML for one pinned revision. Written by the Worker on first request. |

The builder must use the same FNV-1a function as `worker/src/lib/titles.ts`. Add a shared test vector file both sides test against.

### D1 schema (first migration)

```sql
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
```

Retention: a daily cron deletes `shots` and `rounds` older than 30 days and players with no play for 12 months. `page_visits` and `hole_stats` are kept (counts only).

## 5. Hole builder (Python, GitHub Actions only)

Command: `python -m wikigolf_builder build --wiki simplewiki --days 30 --start 2026-12-01 [--upload]`

### 5.1 Read the dumps

- Source: `https://dumps.wikimedia.org/{wiki}/latest/` (or a dated folder): `{wiki}-latest-page.sql.gz`, `-pagelinks.sql.gz`, `-linktarget.sql.gz`, `-redirect.sql.gz`.
- Stream each file over HTTP straight through gzip into the parser. Do not save unzipped files: the Actions machine has 14 GB of disk.
- Parse the `CREATE TABLE` statement at the top of each dump to find column positions. Do not hard-code column order. `pagelinks` uses `pl_from` and `pl_target_id`; `pl_target_id` joins to `linktarget.lt_id` (`lt_namespace`, `lt_title`).
- Keep namespace 0 only. Resolve redirects (follow at most 2 hops) so links to a redirect count as links to its target. Drop self-links and duplicate edges.
- Record each article's revision ID from `page.page_latest`. The Worker serves exactly that revision, so the graph and what players see always match.

### 5.2 Build the graph

- Number articles 0..N−1 (`pageIdx`). Store forward and reverse links as CSR arrays of `int32` (offsets + targets) in NumPy. Use memory-mapped files on disk if RAM gets tight.
- Write `snapshots/{snap}/meta.json` with real counts. Print peak memory and run time in the job summary.

### 5.3 Pick holes

For each date:
1. Draw par from the schedule with `random.Random(date)`. Target shortest distance `d = par − 1`.
2. Candidate targets: articles with 20 to 2,000 incoming links, not excluded (5.4). Fewer incoming links makes long holes possible.
3. One reverse breadth-first search per candidate gives every article's distance to it (`uint8`, 255 = none).
4. Pick a start exactly `d` clicks away with at least 200 incoming links (a well-known page) and not excluded.
5. Score difficulty: fewer distinct shortest routes, fewer target backlinks and less reliance on the 1,000 most-linked articles make it harder. Keep the pair closest to the day's target difficulty.
6. Verify: fetch the Parsoid HTML for each page on one shortest route (Wikimedia REST, `GET https://{lang}.wikipedia.org/w/rest.php/v1/revision/{revId}/html`) and confirm each next link appears as `href="./{Title}"`. If not, drop that edge and search again.
7. No start or target repeats within 365 days. Never reuse a pair.

### 5.4 Exclusions (start and target only)

Disambiguation pages, list pages (`List of …`), years and dates (`1999`, `March 3`), very short articles, and titles in `builder/blocklist.txt` (sensitive topics; reviewed by the owner). Excluded pages can still appear mid-route.

### 5.5 Export and upload

- Write title shards, hole files, distance files and `holes/index.json`.
- Upload with boto3 to R2's S3-compatible endpoint (`https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com`) using `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY`.
- New holes upload with `status: "queued"`. The owner can flip a date to `"approved"` (a small script or a field in `holes/index.json`). The Worker serves `queued` holes in dev and only `approved` holes in production.

### 5.6 Tests

`builder/tests/` uses a hand-made 20-page fixture wiki (SQL dump snippets) with known distances. Test: SQL parsing with reordered columns, redirect resolution, CSR correctness, BFS distances, par and schedule, exclusion rules, and the shared FNV-1a test vectors.

## 6. Worker API

All responses are JSON. All input is validated (use `zod` or hand-written checks). All SQL uses bound parameters.

| Method and path | Does |
| --- | --- |
| `GET /api/hole?date=YYYY-MM-DD` | Hole for that date: number, start, target, par, pick-up, wiki. Accept only dates that are "today" somewhere on Earth (UTC−12 to UTC+14) or in the past. Never return distances. |
| `GET /api/page?title=…` | Resolves the title through the shard index, then returns `{ title, idx, revId, html }` for the pinned revision. HTML comes from R2 `html/` or, on a miss, from the Wikimedia REST revision endpoint (then saved to R2). Set `Cache-Control: public, max-age=31536000, immutable` keyed by revision. |
| `POST /api/rounds` | `{ date }`. Creates a round; ranked if it is the player's first round for a current date, practice otherwise. Sets the player cookie if missing. Returns the round and the start page. |
| `POST /api/rounds/:id/shots` | `{ shotNo, fromIdx, linkTitle }`. Checks below. Returns `{ lie, strokes, toPin, holed, done, page: {title, idx, revId} }`. |
| `POST /api/rounds/:id/mulligan` | Undoes the last shot once per round. |
| `POST /api/rounds/:id/caddie` | `{ linkTitles: string[] }` (first 40 links on the current page, in reading order, sent by the client). Returns the first one that is closer, or none. Adds 1 penalty either way. |
| `GET /api/rounds/:id/result` | Score, time, shots, rarity (or `pending`). Only after the round is done. |
| `GET /api/me` | Streak, best streak, games played, last date. |
| `POST /api/backup-code` | Creates a 4-word code like `maple-fox-orbit-9`; stores only its SHA-256 hash. |
| `POST /api/restore` | `{ code }`. Moves the cookie to the matching player. Rate-limited. |

### Checking a shot

1. Load the round. Reject if done, if `shotNo` is not the next number (a repeated `shotNo` returns the stored answer), or if `fromIdx` is not the round's current page.
2. Confirm the link is on the current page: the cached HTML of the current revision must contain `href="./{encoded linkTitle}"`. A plain substring check is enough and cheap.
3. Resolve `linkTitle` through the shard index to `toIdx` (redirects already folded in).
4. Read both distances from the hole's distance array (loaded from R2 once per Worker instance and kept in memory).
5. Reject any shot that claims to get more than one click closer (`dist(to) < dist(from) − 1`). A real link cannot do that.
6. Lie by the rules table. Save the shot and update the round in one D1 batch. At pick-up, end the round.

### Identity cookie

`wg_pid` = `{uuid}.{hmac}`, signed with `COOKIE_SECRET` (set with `wrangler secret put`). `HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=34560000`. Reject tampered cookies and issue a new ID.

### Scheduled jobs (`scheduled()` handler)

- Every 10 minutes: for today's dates, recompute `page_visits` from finished ranked rounds, then each finisher's rarity, then `hole_stats`. Show rarity as `pending` until 100 people have finished that date.
- Daily: retention deletes (section 4).

Rarity for route r with pages p₁…pₖ between start and target, n(p) finishers through p, N finishers: `c(r) = mean(n(pᵢ)/N)`; `rarity(r) = 100 × share of other finishers' routes with c > c(r)`.

### Security headers

Set on every HTML response: a strict `Content-Security-Policy` (`default-src 'self'; img-src 'self' data:; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.

## 7. Web app

### Screens

| Screen | Notes |
| --- | --- |
| Tee | Pixel course art, hole number and day, start → target, par chip, "Pick up at N strokes", one primary button: TEE OFF, or SEE YOUR RESULT plus "Play a practice round" if today's ranked round is done. Streak line under it. |
| Play | Course bar (hole/par, stroke, fairway strip with ball, flag and the lie tag above the ball), article card, phone dock (Find a link, bag icon). On desktop (≥1024 px) the bag, search and shot list move into a side panel, as in the mock. |
| Find a link | Phone: bottom sheet with search and results. Desktop: always visible in the side panel. |
| Bag | Mulligan (1 per round) and caddie (+1 stroke). |
| Holed | Result word (BIRDIE!, PAR!, …), strokes and time, one square per shot, rarity line, SHARE RESULT (primary), Scorecard and Play again (outlined). |
| Archive | Past dates; each plays as practice. Results only after finishing. |
| Stats | Current and best streak, games played, average against par, this week's round. Backup code: create and restore. |
| How to play, Privacy | Plain-language pages. The privacy page says exactly what is stored (section 8). |

### Article card

- Fetch `/api/page`, parse the HTML with `DOMParser` (an inert document; scripts never run), and build a safe model: title, short description, lead paragraphs, then sections as folded blocks. Each block is a list of `{ text }` and `{ link: title, label }` items. Render with Svelte nodes only.
- Keep `a[rel="mw:WikiLink"]` links to namespace 0. Drop references (`sup.reference`, `.mw-references-wrap`), edit links, hatnotes, maintenance boxes, images and math.
- Infobox → folded "Quick facts". Navigation boxes and tables → folded "More links" list. Every playable link from the HTML must be reachable somewhere on the card.
- Footer on every card: article title linked to `https://{lang}.wikipedia.org/w/index.php?oldid={revId}`, "history" linked to the article history, "CC BY-SA 4.0" linked to the license, and "Shortened and reformatted for Wiki Golf".
- Preload a linked page only on intent (hover, focus or pointerdown), never in bulk, to protect the free request budget.

### Feedback and animation

Match the mock: the lie tag pops in above the ball for 2.2 s, then shows "N TO PIN"; the ball steps along the strip (450 ms, 6 steps); bunker shakes the card (240 ms); a new page slides in (180 ms); holing drops the ball into the cup with pixel confetti. Use CSS `steps()`. Turn all motion off under `prefers-reduced-motion`. No animation blocks input.

### Look

Use the tokens in `design/mock.html` (`--night`, `--grass`, `--fairway`, `--paper`, `--ink`, `--flag`, `--sand`, …). Pixelify Sans for headings, numbers and short labels; Atkinson Hyperlegible for everything else. One solid primary button per screen at most. Controls at least 44 px. Text contrast at least 4.5:1. Visible keyboard focus.

### Local storage

The browser keeps today's result, recent history and settings for fast display. The server is the source of truth for rounds and streaks. Wrap every storage call in try/catch; the game must work with storage disabled.

### Share

Copy to clipboard: `Wiki Golf {holeNo} · {WORD} ({strokes} on a par {par})` then one square per shot (green fairway, brown rough, yellow bunker, flag for holed). No page names.

## 8. Privacy (what the privacy page states)

| Data | Where | Kept for |
| --- | --- | --- |
| Random player ID | Signed cookie, and the server | Until the player clears it |
| Today's result and history | Browser storage | Until the player clears it |
| Rounds: hole, route, strokes, time | Server, keyed by the random ID | 30 days, then reduced to totals |
| Streak summary | Server, keyed by the random ID | Deleted after 12 months without play |
| Page visit counts | Server, no ID attached | Kept |
| Names, emails, IP addresses | Not stored | — |

No ads, no third-party trackers, no analytics cookies.

## 9. Free-tier budgets

| Limit (free plan) | Our use per player per day (target) |
| --- | --- |
| Workers: 100,000 requests/day, 10 ms CPU per request, 50 subrequests per request | About 12 requests (hole, round, ~8 shots, result, pages). Page HTML is cached in R2 and at the edge. |
| D1: 100,000 rows written/day, 5 million rows read/day | About 20 rows written. Batch writes per shot. |
| R2: 10 GB storage, 1 million writes/month, 10 million reads/month | Title shards and HTML cache stay under 10 GB; prune HTML of old snapshots. |

That serves roughly 3,000–5,000 players a day. Log a warning when daily usage passes 70% of any limit. If caddie lookups exceed the subrequest cap, cut the candidate list rather than raising limits. Moving to Workers Paid ($5/month) needs the owner's approval.

## 10. GitHub Actions

| Workflow | Trigger | Does |
| --- | --- | --- |
| `ci.yml` | Pull requests and pushes | Typecheck, lint, `vitest` (shared, worker, web), `pytest` (builder with fixtures) |
| `deploy.yml` | Push to `main` | Build web, `wrangler d1 migrations apply --remote`, `wrangler deploy` |
| `build-holes.yml` | Manual (`wiki`, `days`, `start`) and monthly schedule | Run the builder with `--upload`; `timeout-minutes: 350`; write a job summary table of new holes, counts, peak memory and run time |

Secrets the owner adds in GitHub (Settings → Secrets and variables → Actions): `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.

## 11. Phases

Work in order. Each phase ends with its "Done when" check passing and `PROGRESS.md` updated. Stop and report after each phase.

### Phase 0 — Scaffold
- npm workspaces, TypeScript strict, ESLint, Prettier, Vitest; Svelte 5 + Vite app; Hono Worker with static assets and SPA fallback; `wrangler.jsonc` with D1 and R2 bindings; `ci.yml`.
- Create the R2 bucket and D1 database with Wrangler (`wrangler r2 bucket create wiki-golf`, `wrangler d1 create wiki-golf`) and record the IDs in `wrangler.jsonc`.
- Ask the owner to create R2 S3 credentials (R2 → Manage API tokens → Object Read & Write, bucket `wiki-golf` only) and add them as GitHub secrets.
- Done when: `npm run dev` serves the tee screen styled like the mock, and CI is green.

### Phase 1 — Hole builder on Simple English
- Everything in section 5, plus `build-holes.yml`.
- Done when: a manual run with `wiki=simplewiki, days=30` uploads 30 holes, shards and distance files to R2, and the job summary shows each hole with one verified shortest route.

### Phase 2 — Worker API
- Everything in section 6, with tests using `@cloudflare/vitest-pool-workers` and a small fixture snapshot.
- Done when: a test plays a full hole through the API (start, shots including a bunker, mulligan, caddie, holing), a faked shot is rejected, and a second round on the same date is practice.

### Phase 3 — Web app
- Everything in section 7, built against the live dev API with `simplewiki` holes.
- Done when: a full hole plays in the browser at 390 px and 1280 px widths, Lighthouse accessibility is 95 or higher, and the gzipped JavaScript is under 150 KB.

### Phase 4 — Scores, streaks and privacy
- Ranked vs practice, archive, stats, backup code, rarity and retention crons, privacy page.
- Done when: streaks survive a cleared browser via backup code, rarity shows after 100 finishers in a seeded test, and the retention job deletes 31-day-old rows in a test.

### Phase 5 — Deploy and beta
- `deploy.yml`; deploy to the free `workers.dev` address; smoke test on phone and desktop browsers.
- Done when: the owner can share the link and friends can play the day's hole end to end.

### Phase 6 — Full English Wikipedia
- Run `build-holes.yml` with `wiki=enwiki`. Measure peak memory, disk and time.
- If it fails on the 16 GB / 14 GB Actions machine: first reduce memory (memory-mapped arrays, chunked edge sorting). If still too big, add a fallback workflow that creates a Hetzner Cloud server with 32 GB RAM via the `hcloud` CLI, runs the build there, uploads, and always deletes the server at the end (billing continues until deletion). This needs an `HCLOUD_TOKEN` secret and the owner's approval first.
- Done when: 30 `enwiki` holes are in R2 and production serves them.

### Phase 7 — Launch checklist
- Owner confirms the name against Wikimedia's trademark policy.
- Privacy page live; attribution footer on every card; CSP and headers verified.
- Usage alerts at 70% of free limits; 14 days of approved holes queued.
- Done when: the owner signs off.

## 12. Open questions for the owner

Record answers in `PROGRESS.md` when they come in.

- Launch date (`HOLE_EPOCH`).
- Topics for `builder/blocklist.txt`.
- Whether to allow a "Back" move, and its cost.
- Whether one missed day a week keeps a streak alive.
