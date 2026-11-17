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
- [ ] Manual run with `wiki=simplewiki, days=30` uploads 30 holes, shards and distance files to R2 (job summary shows date/hole/par/route-check only)

### Notes and decisions

- **Extra dump file:** `page_props` is downloaded too (≈10 MB for simplewiki); it is the reliable source for disambiguation pages (plan 5.4).
- **Redirects:** a link to a redirect counts as a link to its target (plan 5.1). Route verification resolves each `href="./…"` through the same title map, so a hop via a redirect link passes. The Worker's Phase 2 link check must do the same, not just a raw `href="./{target}"` substring match.
- **Titles** are stored in underscore form (`Apollo_11`) everywhere, matching the dumps and the title index.
- **Difficulty** = mean of three 0–1 terms: fewer shortest routes, fewer target backlinks, fewer hub pages (top 1,000 by in-links) on shortest routes. Target per weekday: Mon–Tue 0.35, Wed–Thu 0.45, Fri–Sat 0.55, Sun 0.65 (`builder/wikigolf_builder/config.py`).
- **Thresholds:** start/target must be at least 2,000 bytes (simplewiki) or 5,000 bytes (enwiki) to count as "not very short". Each date tries up to 40 random candidate targets and 12 starts per target.
- **No overwrites:** the builder skips dates already in `holes/index.json` and never re-uploads an existing hole or snapshot. It never deletes anything in R2.
- **Index:** `holes/index.json` includes start/target titles for the no-repeat rules (recorded in plan section 4).
- **Spoilers (decided 2026-11-17):** routes and endpoints stay out of the public Actions logs. The build step log and the job summary show only date, hole number, par and route-check result; the per-hole progress line and the dropped-link line carry no titles either. The owner reviews start/target privately with `show` before `approve`. The route itself is never stored in R2 (it would be served to clients), so `show` reviews the start and target articles — the two endpoints a hole can get wrong.
- **Blocklist:** `builder/blocklist.txt` is a conservative starter list for the owner to review and extend. Actual slur words are deliberately not written into this public file; add specific slur-titled articles during private review. "Recent" deaths/disasters can't be captured statically — review each build's queued holes with `show`.
- **Memory:** edges are de-duplicated with one in-memory `np.unique` over int64 keys. Fine for simplewiki; for enwiki (~1.5 billion link rows) Phase 6 will need chunked sorting or memory-mapped arrays, as the plan anticipates.

## Open questions for the owner

| Question                                        | Answer                                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Launch date (`HOLE_EPOCH`)                      | Keep the placeholder `2026-12-01` (now in `shared/config.json`) for now (owner, 2026-11-17) |
| Topics for `builder/blocklist.txt`              | —                                                                                           |
| Allow a "Back" move, and its cost?              | —                                                                                           |
| Does one missed day a week keep a streak alive? | —                                                                                           |
