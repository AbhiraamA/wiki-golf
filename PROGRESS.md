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
- **Difficulty** = mean of three 0–1 terms: fewer shortest routes, fewer target backlinks, fewer hub pages (top 1,000 by in-links) on shortest routes. Target per weekday: Mon–Tue 0.35, Wed–Thu 0.45, Fri–Sat 0.55, Sun 0.65 (`builder/wikigolf_builder/config.py`).
- **Thresholds:** start/target must be at least 2,000 bytes (simplewiki) or 5,000 bytes (enwiki) to count as "not very short". Each date tries up to 40 random candidate targets and 12 starts per target.
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

## Open questions for the owner

| Question                                        | Answer                                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Launch date (`HOLE_EPOCH`)                      | Keep the placeholder `2026-12-01` (now in `shared/config.json`) for now (owner, 2026-11-17) |
| Topics for `builder/blocklist.txt`              | —                                                                                           |
| Allow a "Back" move, and its cost?              | —                                                                                           |
| Does one missed day a week keep a streak alive? | —                                                                                           |
