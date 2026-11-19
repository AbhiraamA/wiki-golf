# Wiki Golf — Progress

Running checklist for `plan.md`. Ticked items have landed.

## Phase 0 — Scaffold

- [x] npm workspaces: `shared`, `web`, `worker`
- [x] TypeScript strict (`tsconfig.base.json`), ESLint (flat config, typescript-eslint strict, svelte), Prettier, Vitest in every workspace
- [x] ESLint guard for hard rule 2: `svelte/no-at-html-tags` and `innerHTML`/`outerHTML` are errors
- [x] `shared/`: `config.ts` (User-Agent, `HOLE_EPOCH`), `schedule.ts` (hole number, weekday, par range), `rules.ts` (par, pick-up, lies, result word), `types.ts`, with tests
- [x] Svelte 5 + Vite app with the tee screen styled like `design/mock.html` (tokens, pixel art, how-to-play sheet), using a placeholder hole until the API exists
- [x] Hono Worker: `/api/health`, JSON 404 for unknown `/api/*`, everything else served from Workers Static Assets with SPA fallback (`run_worker_first: ["/api/*"]`)
- [x] `worker/wrangler.jsonc` with `DB` (D1), `BUCKET` (R2) and `ASSETS` bindings, `WIKI=simplewiki`
- [x] Worker tests in the Workers runtime (`@cloudflare/vitest-plugin`)
- [x] `.github/workflows/ci.yml`: typecheck, lint, format check, test, build
- [x] `npm run dev` serves the tee screen (Vite on :5173, proxying `/api` to `wrangler dev` on :8787); checked at 390 px and 1280 px
- [x] **Owner:** enable R2 on the Cloudflare account
- [x] Create R2 bucket `wiki-golf` (`BUCKET` binding in `worker/wrangler.jsonc`)
- [x] Create D1 database `wiki-golf` (region ENAM, id `4fd16e0f-2c71-4fda-8d92-e07f03bbfd44`) and record it in `worker/wrangler.jsonc`
- [x] **Owner:** create R2 S3 credentials (R2 → Manage API tokens → Object Read & Write, bucket `wiki-golf` only) and add GitHub secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
- [x] CI green on GitHub (PR #1). CI runs Node 24: Node 22 ships npm 10, which rejects the npm 11 lockfile

### Notes and deviations

The owner approved these deviations on 2026-11-17.

- `@cloudflare/vitest-pool-workers` (named in the plan) is deprecated and renamed `@cloudflare/vitest-plugin`; using the successor. It needs Vitest 4, so Vitest is pinned to `~4.1`.
- TypeScript is pinned to `~6.0` because typescript-eslint and svelte-check do not support TypeScript 7 yet.
- `npm audit` reports advisories in dev-only dependencies pulled in by wrangler/miniflare (undici, sharp, picomatch). Nothing ships to users; revisit when wrangler updates.
- The tee screen's TEE OFF button does nothing yet; the play screen is Phase 3. The streak line shows a placeholder.
- D1 migrations (schema in plan section 4) are left for Phase 2, where they are first used.
- CI's `builder` job (ruff, pytest) was added in Phase 1.

## Phase 1 — Hole builder on Simple English

- [x] `builder/` Python 3.12 package: `net` (User-Agent, single connection, backoff on 429/5xx, resumable downloads), `dumps` (newest complete dump via `dumpstatus.json`), `sqlparse` (columns from `CREATE TABLE`, both row layouts), `graph` (CSR, redirects ≤ 2 hops, self-links and duplicates dropped), `bfs`, `exclude`, `pick` (par from `random.Random(date)`, difficulty, no-repeat rules), `verify` (Parsoid HTML route check, drops missing links and searches again), `export`, `upload` (boto3 to R2), `cli`
- [x] `shared/config.json`: one source for `holeEpoch`, app version, contact, shard counts and page chunk size, read by both TypeScript and Python
- [x] FNV-1a in `shared/src/hash.ts` and `builder/wikigolf_builder/fnv.py`, both tested against `shared/test-vectors/fnv1a.json`
- [x] 20-page fixture wiki (`builder/tests/fixtures/`) and 32 tests: SQL parsing with reordered columns, escapes and chunk boundaries; redirects; CSR; BFS distances; par schedule; exclusions; picking, HTML verification and retry; no-repeat rules; end-to-end CLI output
- [x] Parser checked against the first 1 MB of each real `simplewiki-20261001` table and one real Parsoid page
- [x] `.github/workflows/build-holes.yml` (manual + monthly, `timeout-minutes: 350`, job summary with holes, counts, peak memory, timings, disk)
- [x] CI `builder` job: ruff check, ruff format check, pytest
- [x] Pages file layout decided and recorded in `plan.md` section 4 (chunks of 1000)
- [x] `show` command (local review): `python -m wikigolf_builder show --status queued` prints each hole's start, target, par, difficulty and pinned-revision links from R2; needs the R2 env vars
- [x] `approve` command: `python -m wikigolf_builder approve --dates 2026-12-01 …` or `--through 2026-12-14` (add `--dry-run` to preview); needs the R2 env vars
- [x] Public build logs and job summary carry no start, target or route (owner decision, 2026-11-17); endpoints are reviewed privately with `show`
- [x] Starter `builder/blocklist.txt` drafted for owner review (violent events/atrocities, sexual content, suicide/self-harm, deaths/disasters, slurs, extremist groups, divisive political figures)
- [x] Manual run (`wiki=simplewiki, days=30, start=2026-11-18, upload`) succeeded: run [44175160227](https://github.com/AbhiraamA/wiki-golf/actions/runs/44175160227). Snapshot `simplewiki-20261101` (286,136 articles, 13.0M links); 30/30 holes built and route-verified; 413 R2 objects written (352 snapshot files + 30×2 hole/distance + index). Peak memory 1.2 GB, run 5m23s. 1 link dropped at the HTML check and the route re-found. Job summary showed date/hole/par/route-check only — no titles or routes. Holes are `queued`, pending `show` review and `approve`.

### Notes and decisions

- **Extra dump file:** `page_props` is downloaded too (≈10 MB for simplewiki); it is the reliable source for disambiguation pages (plan 5.4).
- **Redirects:** a link to a redirect counts as a link to its target (plan 5.1). Route verification resolves each `href="./…"` through the same title map, so a hop via a redirect link passes. The Worker's Phase 2 link check must do the same, not just a raw `href="./{target}"` substring match.
- **Titles** are stored in underscore form (`Apollo_11`) everywhere, matching the dumps and the title index.
- **Fame filter (2026-11-17; superseded 2026-11-18 — see "Builder revision" below):** both endpoints must be recognisable, measured by incoming-link count. Targets sit in the top `target_top_fraction` of articles by inlinks (default 3%). Starts are **tiered by hole length** (owner decision): short holes (distance < `long_distance`, i.e. par 3–5) require the top `start_top_fraction_short` (default 8%); long holes (par 6–7) keep the looser top `start_top_fraction_long` (default 20%), because few famous articles sit 5–6 clicks from a famous target, so a tight bar would leave long holes unbuildable. Both endpoints must be above `min_page_len` (not stubs) and not excluded. Thresholds are config values (`PickSettings`), overridable with `--pick`. This replaced the earlier absolute inlink thresholds that let obscure pages (e.g. "Ninna", a compilation album) be chosen. A local check (2026-11-17) confirmed targets became recognisable (Hotel, Biology, NBC News, Aircraft, …); the tier tightens short-hole starts, which were the weakest.
- **Exclusions** now also drop music works by their disambiguator — `(album)`, `(song)`, `(single)`, `(EP)`, `(soundtrack)`, `(… song)` etc. — and `…_discography`. Non-disambiguated album/song titles (e.g. a bare "Thriller") aren't caught by title alone; the fame filter handles the long tail, since obscure albums fall below the inlink cut. (No category dump is parsed.)
- **Difficulty comes from distance, not obscurity (2026-11-17):** `difficulty = shortest_distance / 6`, in [0,1]. The old route-count/backlink/hub scoring and the per-weekday difficulty targets are gone; the picker selects a famous target and a well-known start at the day's distance and no longer optimises for obscurity.
- **Themed days (2026-11-17):** the builder reads a private calendar from R2 `themes.json` (never committed; see `builder/themes.local.json`, gitignored, for a starter the owner uploads). Each theme matches a fixed date, the nth weekday of a month (n=-1 for last), or Easter (±offset), and pins one target or a small pool plus an optional `{label, emoji}` badge. On a themed date the target skips the fame filter (the owner chose it) and may repeat yearly (exempt from the no-repeat rule); the builder finds a well-known start at the day's distance, widening the par by up to `theme_par_widen` (default 1) if needed, logged title-free. The badge is written into the hole file (`badge`) and exposed by `HoleInfo`; the tee screen shows it. Themed dates are logged as "themed" (public — the badge is public; only the target stays secret).
- **Thresholds:** start/target must be at least 2,000 bytes (simplewiki) or 5,000 bytes (enwiki) to count as "not very short". Each date tries up to `candidates_per_day` (default 60) random candidate targets and 12 starts per target.
- **Review without S3 keys (2026-11-17):** `show` and `approve` default to `--via wrangler`, reading/writing R2 through the owner's `wrangler login` (no R2 keys needed), which is how review/approve will work before the enwiki launch. `--via keys` forces the boto3 path. CI uploads and the admin `relayout`/`clear` commands still use S3 keys.
- **Replacing holes:** the builder never overwrites, so `clear --wiki <wiki> --apply` deletes a wiki's holes/distances/index, and `build-holes.yml` has a `reset` input that clears before building.
- **Per-wiki R2 layout (2026-11-17):** holes, distances and the index live under a wiki prefix — `{wiki}/holes/{date}.json`, `{wiki}/distances/{date}.bin`, `{wiki}/holes/index.json`. Snapshots keep `snapshots/{snap}/` (snap already names the wiki). So `simplewiki` test holes can't block `enwiki` launch dates, and the index/no-repeat history is per wiki. The Phase 2 Worker reads `env.WIKI` (already a var in `wrangler.jsonc`) to pick the prefix. `show`/`approve` take `--wiki` (default `simplewiki`).
- **Migration:** the earlier top-level `holes/`+`distances/` objects were moved under `simplewiki/` with `python -m wikigolf_builder relayout --wiki simplewiki --apply --delete-old`, run via the manual `migrate-holes.yml` workflow (it has the R2 secrets). The command is idempotent and verifies each copy before deleting the original.
- **No overwrites:** the builder skips dates already in `{wiki}/holes/index.json` and never re-uploads an existing hole or snapshot. It only deletes via the explicit `relayout --delete-old` admin command.
- **Index:** `holes/index.json` includes start/target titles for the no-repeat rules (recorded in plan section 4).
- **Spoilers (decided 2026-11-17):** routes and endpoints stay out of the public Actions logs. The build step log and the job summary show only date, hole number, par and route-check result; the per-hole progress line and the dropped-link line carry no titles either. The owner reviews start/target privately with `show` before `approve`. The route itself is never stored in R2 (it would be served to clients), so `show` reviews the start and target articles — the two endpoints a hole can get wrong.
- **Blocklist:** `builder/blocklist.txt` is a conservative starter list for the owner to review and extend. Actual slur words are deliberately not written into this public file; add specific slur-titled articles during private review. "Recent" deaths/disasters can't be captured statically — review each build's queued holes with `show`.
- **Memory:** edges are de-duplicated with one in-memory `np.unique` over int64 keys. Fine for simplewiki; for enwiki (~1.5 billion link rows) Phase 6 will need chunked sorting or memory-mapped arrays, as the plan anticipates.

## Phase 2 — Worker API

- [x] D1 migration `0001_init.sql`: full schema from plan section 4 (players, rounds, shots, page_visits, hole_stats; unique ranked index per player+date).
- [x] Identity cookie `wg_pid = {uuid}.{hmac}`, HMAC-SHA-256 signed with `COOKIE_SECRET` (`HttpOnly; Secure; SameSite=Lax; Max-Age=400d`); tampered cookies are rejected and a new id issued. Dev secret in `wrangler.jsonc`; production via `wrangler secret put COOKIE_SECRET`.
- [x] Snapshot reads from R2 (`snapshot.ts`): meta, title shards (FNV-1a → shard, redirects folded), page chunks; per-instance in-memory caches.
- [x] Endpoints: `GET /api/hole` (public info, no distances/route, future dates rejected via the UTC−12…+14 window), `GET /api/page?title=&date=` (resolves via the hole's snapshot, returns pinned-revision HTML, cached immutable), `POST /api/rounds` (sets cookie, creates player, ranked vs practice), `POST /api/rounds/:id/shots`, `/mulligan`, `/caddie`, `GET /api/rounds/:id/result`, `GET /api/me`.
- [x] Shot validation (plan §6): round not done, shot number is next (repeat replays the stored answer), `fromIdx` is the current page, the link is present in the current page's cached HTML, resolves through the shard index, and the distance guard rejects any shot claiming to get more than one click closer. Shot + round update run in one D1 batch; pick-up ends the round at double par.
- [x] HTML article HTML served from R2 or fetched from Wikimedia REST (pinned revision) with the project User-Agent, then cached to R2. The Worker never injects this HTML; it parses links only for shot validation.
- [x] Security headers: CSP, `X-Content-Type-Options`, `Referrer-Policy` on the static front end via `web/public/_headers` (the assets layer serves those paths directly, since `run_worker_first` is only `/api/*`); nosniff + referrer on API responses via middleware.
- [x] Tests (`@cloudflare/vitest-plugin`, migrations applied via `readD1Migrations`, a seeded 4-page fixture snapshot in R2): a full hole played through the API (start, bunker, mulligan, caddie, fairway, holing → PAR), a faked shot rejected, ownership enforced, and a second round on the same date is practice.

### Deferred to Phase 4 (not in this phase)

- `POST /api/backup-code`, `POST /api/restore`, streak updates on ranked finish, rarity computation and the `scheduled()` crons (rarity/page_visits/hole_stats recompute and retention deletes). `GET /api/me` returns the stored player totals, which stay at zero until Phase 4 wires up streak updates. `GET /api/rounds/:id/result` returns `rarity: "pending"` until then.
- `badge` on `HoleInfo`/`shared` is added in both this branch and PR #5; whichever merges second resolves trivially.

## Phase 3 — Web app

- [x] **Article parser** (`web/src/lib/article/`): Parsoid HTML → safe model via `DOMParser` (inert document, no scripts/resources). Keeps only namespace-0 wiki links and text; drops references, edit links, hatnotes, images, math and maintenance boxes; infobox → "Quick facts", navboxes → "More links"; lists every playable link once. Rendered with Svelte nodes only — never `{@html}`/`innerHTML` (lint enforces it).
- [x] **API client** (`lib/api.ts`): typed calls to every endpoint, `credentials: 'include'` for the cookie. In dev with `VITE_MOCK=1` it swaps in an in-memory mock (`lib/mock.ts`, Octopus → Apollo 11) that is tree-shaken out of production — lets the whole game be played and screenshotted without the backend.
- [x] **Game state** (`lib/game.svelte.ts`, Svelte 5 runes): tee → play → holed flow, shot/mulligan/caddie against the API, lie-tag flashes, a client-side toPin stack so a mulligan restores the course position without the server re-sending distances.
- [x] **Screens & components:** Tee (loading/error/already-played states, streak line, how-to sheet), Play (course bar with stepping ball + lie tag, article card, phone dock, phone Find/Bag sheets, desktop side panel with search + bag + shot list), Holed (result word, squares, rarity line, scorecard toggle, share, play-again, confetti + ball drop). Matches `design/mock.html`.
- [x] **Local store** (`lib/store.ts`): today's full result saved per date (so "See your result" rebuilds the overlay offline); every call wrapped in try/catch so the game works with storage disabled.
- [x] **Share** (`lib/share.ts`): clipboard text `Wiki Golf {n} · {WORD} ({strokes} on a par {par})` + one square per shot, no page names.
- [x] **Animations** (CSS `steps()`): lie-tag pop, ball step, bunker shake, page slide-in, hole drop + pixel confetti; all disabled under `prefers-reduced-motion`.
- [x] **Done-when checks:** a full hole plays in the browser at 390px and 1280px (screenshotted via the mock); Lighthouse accessibility **100** (≥95 required); production JS **27 KB gzipped** (<150 KB required).
- [x] Tests (jsdom): the parser (references/edit/interwiki/File links dropped, infobox/navbox surfaced, every link listed once), the mock backend playing a full hole (fairway/bunker/mulligan/caddie/holing), the local store round-trip, and the share text.

### Notes

- **Parser vs. real Parsoid:** tested against crafted Parsoid-like HTML covering the common structures. Real-world robustness (unusual infobox/table shapes) will be refined against live `simplewiki` holes during the Phase 5 beta.
- **jsdom quirk:** this toolchain's jsdom ships a method-less `localStorage` stub; a tiny `web/test/setup.ts` polyfill gives tests a working one. The app itself tolerates a broken/disabled store via try/catch.
- **Not in Phase 3** (plan section 7 lists them, Phase 4 builds them): the Archive, Stats and Privacy pages. Phase 3 is the daily play experience (Tee/Play/Holed) + how-to.

## Builder revision — fame by pageviews + langlinks, short descriptions (2026-11-18)

Owner decision after reviewing the first fame filter: inlinks are inflated by navboxes, so replace them with a real fame score, loosen starts, and show short descriptions.

- **Targets now use two signals** (both `PickSettings`, `--pick`-overridable):
  - **Interlanguage-link count** from the `langlinks` dump (new table in the graph build): the top `target_langlink_fraction` (default 5%). The number of other-language Wikipedias covering a topic is a navbox-proof fame signal. Replaces `target_top_fraction`/inlinks.
  - **English-Wikipedia monthly pageviews** ≥ `min_target_views` (default 30,000), fetched lazily per candidate from the Wikimedia pageview REST API (project User-Agent, ~20 req/s cap, cached). Per-wiki pageview dumps no longer exist (only a ~5.7 GB all-projects monthly file), and Simple English's own traffic is too small to rank by — so fame is judged on the **English article for the same title** (via the `en` langlink, else the same title); a title with no English article is judged on langlinks alone. `--no-pageviews` skips it; local-dump (test) builds are offline automatically.
- **Starts loosened to a light filter** (owner decision): no fame bar at all — a start only has to be a readable article (not a stub/list/year/music page). Removed the tiered `start_top_fraction_short/long` and `long_distance`. Added an "X at the Olympics/Paralympics" exclusion.
- **Short descriptions** (`shortDesc`) written into each hole's start/target: local `wikibase-shortdesc` (page_props) if present, else the Wikidata item description (prefer English, then wiki language; fetched only for the chosen endpoints via `wbgetentities`). Added to `PageRef` (shared), carried through the Worker unchanged, shown under each article on the tee screen and under the pin in the course bar while playing. `show` prints it for review.
- **No-repeat windows split by role (2026-11-18, owner decision):** targets can't repeat within `target_repeat_window_days` (365) and starts within `start_repeat_window_days` (90), tracked separately (`History.target_dates`/`start_dates`). A memorable target rests a year; a start, just the jumping-off point, may return sooner. The exact pair is still never reused.
- **Local review (2026-11-18, done by Claude via `wrangler login`, never in logs/commits):** of 30 rebuilt simplewiki targets, ~26 were clearly strong (countries, famous people, concepts, foods, landmarks) with good Wikidata descriptions. One dud — `ISO 4217` — had high fame signals (linked from every currency page) but is unrecognisable and unaimable, so added an **ISO-standard exclusion** (`^ISO(/IEC)?\d`), which generalises to ISO 3166/8601/639 etc. A second review of the next rebuild caught `Wikiquote` — a Wikimedia sister project, equally unrecognisable/self-referential — so also added a **Wikimedia-projects exclusion** (Wiktionary, Wikisource, Wikidata, MediaWiki, Wikimedia Foundation, and `Wikipedia` itself). Borderline-but-aimable targets (a head of state, a world religion, a historical state, cultural icons, famous athletes) were kept for variety. Kept the **30k enwiki views floor** — it gives a good famous/aimable ratio without starving the long par-6/7 holes. (Also fixed the Olympics exclusion regex: `\b` never matched before an underscore.)
- All builder + web + worker tests, typecheck, lint and format pass.

## Phase 4 — Scores, streaks and privacy (in progress)

- [x] Migration `0002_finish_tracking.sql`: `rounds.recorded_at`, so a finished round is folded into
      durable state exactly once.
- [x] `worker/src/lib/stats.ts`:
  - `recordFinish` — a conditional UPDATE claims the round (`recorded_at` was null); only the claimer
    bumps `games_played`, advances the daily streak (ranked only) and increments the hole's per-page
    finisher tallies. Replays and double-submits never double-count. Wired into `/shots` and
    `/caddie` on finish.
  - `aggregateHoleStats` — writes `hole_stats` (finisher count + score spread) per date; once a date
    has ≥ `RARITY_MIN_FINISHERS` (100) finishers, sets each finisher's `rarity` = percentage who
    scored that well or better.
  - `runRetention` — deletes rounds/shots and per-hole tallies older than `RETENTION_DAYS` (31);
    players are kept.
  - `runScheduled(cron, …)` dispatches: the daily `41 3 * * *` run prunes, the 10-minute run
    aggregates.
- [x] Cron triggers in `wrangler.jsonc`: `["*/10 * * * *", "41 3 * * *"]`; `scheduled()` in
      `index.ts` calls `runScheduled`.
- [x] Tests (`worker/test/stats.test.ts`): record-once + streak advance/reset + practice-only
      counting; rarity stays pending below 100 finishers then computes (done-when check); retention
      deletes 31-day-old rows and keeps the player (done-when check).

### Backup codes (worker)

- [x] Migration `0003_rate_limits.sql`: a PII-free throttle table (bucket/count/reset_at), pruned by
      the retention cron.
- [x] `worker/src/lib/backup.ts`: `createBackupCode` issues a 4-word code (e.g. `maple-fox-orbit-9`)
      and stores only its SHA-256 hash in `players.backup_hash`; `restoreByCode` matches a code's
      hash to a player. A ~128-word list gives ~21M combinations.
- [x] `POST /api/backup-code` (requires a player) and `POST /api/restore` (`{code}` → re-issues that
      player's cookie). Restore is throttled by a global per-minute cap — no IP or other identifier
      is stored, consistent with the privacy page; the code's entropy is the real lock.
- [x] Tests (`worker/test/backup.test.ts`): round-trip restore to a fresh browser, bad/unknown
      codes, the no-player case, and the throttle (asserts only bucket/count/reset_at are stored).

### Web screens (Archive, Stats, Privacy)

- [x] Lightweight view navigation added to `game.svelte.ts` (`view` state + `openView`/`closeView`)
      and a menu in the Tee topbar; no router needed. Play/Holed still take over the screen.
- [x] **Archive** (`screens/Archive.svelte`): lists past holes (HOLE_EPOCH..yesterday, fetched per
      date, 404s skipped), shows the stored result if played, and plays any date as a practice round
      (`game.playDate`). Empty until the first live day (today is before the placeholder epoch).
- [x] **Stats** (`screens/Stats.svelte`): streak/best/games from `/api/me`; average vs par and
      this-week list computed from local history; create-backup-code and restore UI.
- [x] **Privacy** (`screens/Privacy.svelte`): the §8 table and plain-language statements (no IPs,
      no trackers), contact email, app version.
- [x] Date math moved to a plain `lib/dates.ts` (keeps `Date` out of the runes module per the
      svelte lint). Mock backend extended with `backupCode`/`restore` so the dev/screenshot build
      stays complete. Web typecheck, lint, tests and build pass (prod JS ~31 KB gzipped).
- Not yet visually screenshotted at 390/1280 — verified by typecheck/lint/tests/build only.

## Sensitive-topic target filter (2026-11-18)

Owner decision: famous-but-unsavoury articles (Charles Manson, Methamphetamine, Illuminati) were
being chosen as targets; fame signals don't exclude them. Added a target-only sensitive-topic filter
(the destination is shown by name on the tee; a sensitive _mid-route_ page is still fine).

- **`sensitive.py`** (pure, offline-testable): a set of verified Wikidata QIDs for
  `instance of` / `subclass of` / `occupation` (serial killer, murderer, criminal, rapist, war
  criminal, cult leader, drug, psychoactive drug, conspiracy theory, secret society, terrorist
  organisation, drug cartel) plus description-text patterns (murderer/criminal, drug, conspiracy/
  secret society, terrorism, sexual topic). Patterns avoid common false positives ("stimulant drug"
  not bare "stimulant"; "secret society" not "society").
- **`enrich.make_sensitivity`**: local short description offline; when online also fetches the
  Wikidata description + claims. Degrades quietly to "not sensitive" on any network trouble.
- **`pick.Picker`**: checks sensitivity lazily for targets it actually tries (one Wikidata call per
  attempted target, not per shortlisted one); themed targets are owner-chosen and skip the filter.
  `--no-sensitive` disables it. The public job summary reports only an aggregate "Sensitive targets
  skipped: N" — no titles.
- **Blocklist backstop**: verified against live Wikidata that Manson (occupation=criminal) and the
  Illuminati (P31=secret society) are caught automatically, but **Methamphetamine's** Wikidata item
  is merely "group of stereoisomers" with no drug claim — so hard drugs are listed by name in
  `blocklist.txt`, alongside well-known murderers, conspiracy theories and the three named examples.
- Tested: `tests/test_sensitive.py` (the three examples' real data; false-positive guards) and two
  `tests/test_pick.py` cases (a sensitive target is skipped; a themed target ignores the filter).
- Affected approved simplewiki holes to rebuild: **2026-11-29** (Methamphetamine), **2026-12-01**
  (Charles Manson), **2026-12-16** (Illuminati).

## Content policy for endpoints (`builder/CONTENT_GUIDE.md`, 2026-11-19)

The owner added `builder/CONTENT_GUIDE.md` (tiers A–D for what may be a start/target) as the content
policy. Implemented the rules the builder didn't yet enforce, layered cheapest-first as the guide
directs (blocklist → title patterns → Wikidata claims → short-description keywords → agent review).

- **`sensitive.py`** generalised from the target-only sensitive filter into a role-aware policy:
  - `target_policy_reason` and `start_policy_reason` take already-extracted Wikidata fields + the
    short description, so the module stays pure/unit-tested.
  - New rules: **convicted-of** (`P1399` any value → Tier A, both roles); **modern politician**
    (occupation politician `Q82955` or any position held `P39`, and living or died ≥ 1950 → target
    only — settled figures like Disraeli/Napoleon/Vespasian pass); **recent death** (`P570` within
    **12 months** → both roles); **disputed/occupied territory & states with limited recognition**
    (`Q15239622`/`Q2577883`/`Q10711424` → target only); **hate group** (`Q3233801`) and **genocide**
    (`Q41397`) classes; expanded description keywords (massacre, genocide, mass shooting, hate/
    extremism, suicide/self-harm). All QIDs verified against the live Wikidata API.
  - Note: the guide says 90 days for recent deaths; the owner asked for **12 months**, so that is
    what's enforced (`RECENT_DEATH_DAYS = 365`).
- **`enrich.Policy` / `make_policy`**: one cached Wikidata fetch per item (descriptions + P31/P279/
  P106/P39/P1399/P570), exposing `target_reason`/`start_reason`. `fields_by_title` fetches the same
  by site+title (no dump needed) for the review command. Degrades quietly to "allowed" offline/on
  network trouble (local short description still checked).
- **`exclude.py`** title patterns added: `"X in Y"`/`"Topic of Place"` index pages and `(episode)`/
  `(TV series)`/`(season)` single works. Fixed the `\b`-before-underscore gap in the work
  disambiguator (same bug class as the old Olympics regex).
- **`blocklist.txt`**: disputed-territories backstop section (Abkhazia, South Ossetia, Transnistria,
  Northern Cyprus, Artsakh/Nagorno-Karabakh, Somaliland, Western Sahara).
- **`cli.py check`**: re-checks R2 holes against the policy (start + target), prints PASS/FAIL with
  reasons for local review, exits non-zero if any fail. This is the guide's final review step — run
  on every batch before `approve`.
- **Picker** now uses `make_policy(...).target_reason` as its target filter (was the narrower
  sensitive check); starts rely on the offline blocklist/patterns (online per-start checks would be
  too costly). Themed targets still skip the filter.
- Re-checked all 30 approved simplewiki holes with `check` and re-rolled every failure (CI build on
  the pinned `simplewiki-20261101` snapshot, then re-reviewed and re-approved). Over three rounds:
  2026-11-19 Abkhazia→(Aisha, blocklisted)→**Great Britain**; 2026-11-25 Dilma Rousseff→**Siberia**;
  2026-12-01 Che Guevara→**Sleeping Beauty (1959 film)**; 2026-12-14 Tony Blair→**Copyright**;
  2026-12-18 Boxer Rebellion→**George Washington** (settled history, d. 1799, passes). Final state:
  30/30 approved and passing `check`.
- **Known gap / review reliance:** religious figures and "historical dictators" have no clean
  Wikidata class, so they're caught by the blocklist + the `check`/`show` review step, not
  automatically. Start-side enforcement is offline (blocklist + title patterns) only.

## Phase 5 — Deploy and beta (in progress)

- [x] `.github/workflows/deploy.yml`: on push to `main` (and manual dispatch) — `npm ci`, build the
      front end, `wrangler d1 migrations apply wiki-golf --remote`, `wrangler deploy --var
    ENVIRONMENT:production`, then push the `COOKIE_SECRET` repo secret to the Worker with
      `wrangler secret put` (every deploy, to stay in sync / support rotation).
- [x] Production fail-closed guard (`worker/src/lib/guard.ts`): a `*` middleware returns 503 for
      every request when `ENVIRONMENT=production` and `COOKIE_SECRET` is missing or still the public
      dev default, so the site never serves with forgeable identity cookies. Unit-tested.
- [x] Screenshot pass on Archive/Stats/Privacy at 390 and 1280 (headless Chromium, mock build);
      fixed a mock-only circular-import deadlock by extracting `ApiError` to `web/src/lib/errors.ts`.
- [ ] Owner merges PR #9 → `deploy.yml` deploys to `https://wiki-golf.<subdomain>.workers.dev`.
- [ ] Smoke test on phone + desktop; then set the real `HOLE_EPOCH` launch date.

## Open questions for the owner

| Question                                        | Answer                                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Launch date (`HOLE_EPOCH`)                      | Keep the placeholder `2026-12-01` (now in `shared/config.json`) for now (owner, 2026-11-17) |
| Topics for `builder/blocklist.txt`              | —                                                                                           |
| Allow a "Back" move, and its cost?              | —                                                                                           |
| Does one missed day a week keep a streak alive? | —                                                                                           |
