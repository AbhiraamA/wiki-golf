<script lang="ts">
  import HowToPlaySheet from '../components/HowToPlaySheet.svelte';
  import TeeArt from '../components/TeeArt.svelte';
  import type { Game } from '../lib/game.svelte';

  let { game }: { game: Game } = $props();

  let howOpen = $state(false);

  const hole = $derived(game.hole);
  const streak = $derived(game.me?.streakCurrent ?? 0);
  const streakText = $derived(
    streak > 0 ? `${streak}-day streak` : 'Finish today’s hole to start a streak',
  );
</script>

<section class="screen tee" aria-labelledby="tee-title">
  <div class="topbar">
    <span class="wordmark">WIKI GOLF</span>
    <button
      class="icon-btn how-btn"
      type="button"
      aria-label="How to play"
      onclick={() => (howOpen = true)}>?</button
    >
  </div>

  <TeeArt />

  {#if game.loading}
    <p class="muted" style="margin-top:40px">Loading today’s hole…</p>
  {:else if game.error}
    <p class="played-note" style="margin-top:40px">{game.error}</p>
    <div class="tee-actions">
      <button class="btn-primary" type="button" onclick={() => game.init()}>TRY AGAIN</button>
    </div>
  {:else if hole}
    <div class="tee-info">
      <span class="eyebrow">{game.eyebrow}</span>
      <h1 class="route-title" id="tee-title">
        {hole.start.title.replace(/_/g, ' ')}<br /><span class="to">to</span>
        {hole.target.title.replace(/_/g, ' ')}
      </h1>
      <div class="par-row">
        <span class="par-chip">PAR {hole.par}</span>
        <span class="muted">Pick up at {hole.pickUp} strokes</span>
      </div>
      {#if game.alreadyPlayed}
        <p class="played-note">
          You finished today’s hole. Come back tomorrow for hole {hole.holeNo + 1}, or play a
          practice round.
        </p>
      {/if}
    </div>

    <div class="tee-actions">
      {#if game.alreadyPlayed}
        <button class="btn-primary" type="button" onclick={() => game.seeResult()}>
          SEE YOUR RESULT
        </button>
        <button class="btn-ghost" type="button" onclick={() => game.teeOff(true)}>
          Play a practice round
        </button>
      {:else}
        <button
          class="btn-primary"
          type="button"
          disabled={game.busy}
          onclick={() => game.teeOff(false)}
        >
          TEE OFF
        </button>
      {/if}
      <div class="tee-foot"><span>{streakText}</span></div>
    </div>
  {/if}
</section>

{#if howOpen}
  <HowToPlaySheet onclose={() => (howOpen = false)} />
{/if}

<style>
  .tee {
    padding: 16px 24px 32px;
    overflow-y: auto;
  }
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-right: -12px;
  }
  .wordmark {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 1px;
  }
  .how-btn {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 700;
  }
  .tee-info {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 40px;
  }
  .eyebrow {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--mist);
  }
  .route-title {
    margin: 0;
    font-family: var(--font-display);
    font-size: clamp(30px, 8vw, 36px);
    font-weight: 600;
    line-height: 1.15;
    text-wrap: balance;
  }
  .route-title .to {
    color: var(--mist);
  }
  .par-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 8px;
    flex-wrap: wrap;
  }
  .par-chip {
    padding: 6px 10px;
    background: var(--sand);
    color: var(--ink);
    font-family: var(--font-display);
    font-size: 18px;
    font-weight: 700;
    line-height: 1;
  }
  .played-note {
    margin: 4px 0 0;
    padding: 12px 14px;
    border: 2px solid var(--outline);
    font-size: 15px;
    line-height: 1.4;
  }
  .tee-actions {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: auto;
    padding-top: 32px;
  }
  .tee-foot {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    min-height: 44px;
    color: var(--mist);
    font-size: 14px;
    flex-wrap: wrap;
  }
  @media (min-width: 1024px) {
    .tee {
      width: 100%;
      max-width: 560px;
      margin: 0 auto;
    }
  }
</style>
