<script lang="ts">
  import { weekday } from '@wiki-golf/shared';
  import type { Game } from '../lib/game.svelte';

  let { game }: { game: Game } = $props();

  const me = $derived(game.me);
  const s = $derived(game.stats());

  function toParText(n: number | null): string {
    if (n === null) return '—';
    const r = Math.round(n * 10) / 10;
    if (r === 0) return 'Even';
    return r > 0 ? `+${r}` : `${r}`;
  }

  // Backup code UI.
  let code = $state<string | null>(null);
  let making = $state(false);
  let codeError = $state(false);

  async function makeCode(): Promise<void> {
    making = true;
    codeError = false;
    const c = await game.makeBackupCode();
    if (c) code = c;
    else codeError = true;
    making = false;
  }

  // Restore UI.
  let restoreInput = $state('');
  let restoring = $state(false);
  let restoreMsg = $state<string | null>(null);
  let restoreOk = $state(false);

  async function doRestore(): Promise<void> {
    restoring = true;
    restoreMsg = null;
    const err = await game.restore(restoreInput);
    restoreOk = err === null;
    restoreMsg = err ?? 'Progress restored to this browser.';
    if (restoreOk) restoreInput = '';
    restoring = false;
  }
</script>

<section class="screen subpage" aria-labelledby="st-title">
  <header class="subbar">
    <button class="btn-ghost back" type="button" onclick={() => game.closeView()}>← Back</button>
    <h1 id="st-title">Stats</h1>
  </header>

  <div class="subbody">
    <div class="grid" role="list">
      <div class="stat" role="listitem">
        <span class="num">{me?.streakCurrent ?? 0}</span><span class="lbl">Day streak</span>
      </div>
      <div class="stat" role="listitem">
        <span class="num">{me?.streakBest ?? 0}</span><span class="lbl">Best streak</span>
      </div>
      <div class="stat" role="listitem">
        <span class="num">{me?.gamesPlayed ?? 0}</span><span class="lbl">Games played</span>
      </div>
      <div class="stat" role="listitem">
        <span class="num">{toParText(s.avgToPar)}</span><span class="lbl">Avg vs par</span>
      </div>
    </div>

    <h2>This week</h2>
    {#if s.thisWeek.length === 0}
      <p class="muted">No ranked rounds yet this week. Play today’s hole to start.</p>
    {:else}
      <ul class="week">
        {#each s.thisWeek as r (r.date)}
          <li>
            <span class="day">{weekday(r.date)}</span>
            <span class="word">{r.word}</span>
            <span class="muted">{r.strokes} on par {r.par}</span>
          </li>
        {/each}
      </ul>
    {/if}

    <h2>Backup code</h2>
    <p class="muted">
      Your progress lives in this browser’s cookie. Make a backup code to move it to another device,
      or to get it back if you clear your browser.
    </p>
    {#if code}
      <p class="code" aria-live="polite">{code}</p>
      <p class="muted small">Write it down — it’s shown only once and replaces any earlier code.</p>
    {:else}
      <button class="btn-ghost wide" type="button" disabled={making} onclick={makeCode}>
        {making ? 'Creating…' : 'Create a backup code'}
      </button>
      {#if codeError}<p class="msg bad">Could not create a code. Try again.</p>{/if}
    {/if}

    <h2>Restore</h2>
    <form
      class="restore"
      onsubmit={(e) => {
        e.preventDefault();
        void doRestore();
      }}
    >
      <label class="sr-only" for="restore-code">Backup code</label>
      <input
        id="restore-code"
        type="text"
        placeholder="maple-fox-orbit-9"
        autocomplete="off"
        autocapitalize="none"
        spellcheck="false"
        bind:value={restoreInput}
      />
      <button class="btn-ghost" type="submit" disabled={restoring}>
        {restoring ? '…' : 'Restore'}
      </button>
    </form>
    {#if restoreMsg}<p class="msg" class:bad={!restoreOk} class:ok={restoreOk}>{restoreMsg}</p>{/if}
  </div>
</section>

<style>
  .subpage {
    padding: 16px 24px 32px;
  }
  .subbody {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 4px;
  }
  .stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 14px;
    border: 2px solid var(--outline);
  }
  .stat .num {
    font-family: var(--font-display);
    font-size: 30px;
    font-weight: 700;
    line-height: 1;
  }
  .stat .lbl {
    font-size: 13px;
    color: var(--mist);
  }
  h2 {
    margin: 18px 0 2px;
    font-family: var(--font-display);
    font-size: 18px;
    font-weight: 700;
  }
  p {
    margin: 0;
    line-height: 1.45;
  }
  .small {
    font-size: 13px;
  }
  .week {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .week li {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 8px 10px;
    border: 2px solid var(--outline);
  }
  .week .day {
    flex: none;
    width: 3.2em;
    font-weight: 700;
  }
  .week .word {
    flex: 1;
    font-family: var(--font-display);
  }
  .code {
    padding: 14px;
    background: var(--sand);
    color: var(--ink);
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 1px;
    text-align: center;
    user-select: all;
  }
  .restore {
    display: flex;
    gap: 8px;
  }
  .restore input {
    flex: 1;
    min-width: 0;
    padding: 0 12px;
    height: 48px;
    border: 2px solid var(--outline);
    background: var(--night);
    color: var(--paper);
  }
  .msg {
    font-size: 14px;
  }
  .msg.bad {
    color: var(--flag);
  }
  .msg.ok {
    color: var(--green);
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
  @media (min-width: 1024px) {
    .subpage {
      width: 100%;
      max-width: 560px;
      margin: 0 auto;
    }
  }
</style>
