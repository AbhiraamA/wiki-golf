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
- [ ] **Owner:** create R2 S3 credentials (R2 → Manage API tokens → Object Read & Write, bucket `wiki-golf` only) and add GitHub secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
- [x] CI green on GitHub (PR #1). CI runs Node 24: Node 22 ships npm 10, which rejects the npm 11 lockfile

### Notes and deviations

The owner approved these deviations on 2026-11-17.

- `@cloudflare/vitest-pool-workers` (named in the plan) is deprecated and renamed `@cloudflare/vitest-plugin`; using the successor. It needs Vitest 4, so Vitest is pinned to `~4.1`.
- TypeScript is pinned to `~6.0` because typescript-eslint and svelte-check do not support TypeScript 7 yet.
- `npm audit` reports advisories in dev-only dependencies pulled in by wrangler/miniflare (undici, sharp, picomatch). Nothing ships to users; revisit when wrangler updates.
- The tee screen's TEE OFF button does nothing yet; the play screen is Phase 3. The streak line shows a placeholder.
- D1 migrations (schema in plan section 4) are left for Phase 2, where they are first used.
- CI has no `builder` (pytest) job yet; it is added with the builder in Phase 1.

## Phase 1 — Hole builder on Simple English

Not started.

## Open questions for the owner

| Question                                        | Answer                                                                                  |
| ----------------------------------------------- | --------------------------------------------------------------------------------------- |
| Launch date (`HOLE_EPOCH`)                      | Keep the placeholder `2026-12-01` in `shared/src/config.ts` for now (owner, 2026-11-17) |
| Topics for `builder/blocklist.txt`              | —                                                                                       |
| Allow a "Back" move, and its cost?              | —                                                                                       |
| Does one missed day a week keep a streak alive? | —                                                                                       |
