<script lang="ts">
  import { weekday, type HoleInfo } from '@wiki-golf/shared';
  import { api } from '../lib/api';
  import { pastDates } from '../lib/dates';
  import type { Game } from '../lib/game.svelte';
  import { savedResult, type StoredResult } from '../lib/store';

  let { game }: { game: Game } = $props();

  interface Entry {
    date: string;
    hole: HoleInfo;
    result: StoredResult | null;
  }

  let entries = $state<Entry[]>([]);
  let loading = $state(true);

  async function load(): Promise<void> {
    loading = true;
    const dates = pastDates(game.date);
    const settled = await Promise.allSettled(dates.map((d) => api.hole(d)));
    entries = settled.flatMap((r, i): Entry[] => {
      const date = dates[i];
      if (!date || r.status !== 'fulfilled') return [];
      return [{ date, hole: r.value, result: savedResult(date) }];
    });
    loading = false;
  }

  void load();
</script>

<section class="screen subpage" aria-labelledby="ar-title">
  <header class="subbar">
    <button class="btn-ghost back" type="button" onclick={() => game.closeView()}>← Back</button>
    <h1 id="ar-title">Archive</h1>
  </header>

  <div class="subbody">
    <p class="muted intro">
      Past holes. Each one plays as a practice round and won’t affect your streak.
    </p>

    {#if loading}
      <p class="muted">Loading past holes…</p>
    {:else if entries.length === 0}
      <p class="muted">No past holes yet — check back after the first day.</p>
    {:else}
      <ul class="list">
        {#each entries as e (e.date)}
          <li>
            <button class="row" type="button" onclick={() => game.playDate(e.date)}>
              <span class="meta">
                <span class="no">#{e.hole.holeNo}</span>
                <span class="day">{weekday(e.date)}</span>
                <span class="par">PAR {e.hole.par}</span>
              </span>
              <span class="route">
                {e.hole.start.title.replace(/_/g, ' ')} → {e.hole.target.title.replace(/_/g, ' ')}
              </span>
              <span class="status">
                {#if e.result}
                  <span class="word">{e.result.word}</span>
                  <span class="muted">{e.result.strokes} on par {e.result.par}</span>
                {:else}
                  <span class="muted">Play ›</span>
                {/if}
              </span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
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
  .intro {
    margin: 0;
    line-height: 1.45;
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .row {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px 14px;
    border: 2px solid var(--outline);
    background: transparent;
    color: var(--paper);
    text-align: left;
    cursor: pointer;
  }
  .row:hover {
    border-color: var(--mist);
  }
  .meta {
    display: flex;
    align-items: baseline;
    gap: 10px;
    font-family: var(--font-display);
    font-size: 14px;
  }
  .meta .par {
    margin-left: auto;
    color: var(--sand);
  }
  .route {
    font-size: 15px;
    line-height: 1.3;
  }
  .status {
    display: flex;
    gap: 8px;
    align-items: baseline;
    font-size: 14px;
  }
  .status .word {
    font-family: var(--font-display);
    font-weight: 700;
    color: var(--green);
  }
  @media (min-width: 1024px) {
    .subpage {
      width: 100%;
      max-width: 560px;
      margin: 0 auto;
    }
  }
</style>
