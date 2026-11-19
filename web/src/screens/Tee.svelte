<script lang="ts">
  import HowToPlaySheet from '../components/HowToPlaySheet.svelte';
  import TeeArt from '../components/TeeArt.svelte';
  import type { Game } from '../lib/game.svelte';

  let { game }: { game: Game } = $props();

  let howOpen = $state(false);
  let menuOpen = $state(false);

  const hole = $derived(game.hole);
  const streak = $derived(game.me?.streakCurrent ?? 0);
  const streakText = $derived(
    streak > 0 ? `${streak}-day streak` : 'Finish today’s hole to start a streak',
  );
</script>

<section class="screen tee" aria-labelledby="tee-title">
  <div class="topbar">
    <span class="wordmark">WIKI GOLF</span>
    <div class="topbar-actions">
      <button
        class="icon-btn how-btn"
        type="button"
        aria-label="How to play"
        onclick={() => (howOpen = true)}>?</button
      >
      <div class="menu-wrap">
        <button
          class="icon-btn how-btn"
          type="button"
          aria-haspopup="true"
          aria-expanded={menuOpen}
          aria-label="Menu"
          onclick={() => (menuOpen = !menuOpen)}>☰</button
        >
        {#if menuOpen}
          <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
          <div class="menu-backdrop" onclick={() => (menuOpen = false)}></div>
          <ul class="menu" role="menu">
            <li role="none">
              <button role="menuitem" type="button" onclick={() => game.openView('archive')}>
                Archive
              </button>
            </li>
            <li role="none">
              <button role="menuitem" type="button" onclick={() => game.openView('stats')}>
                Stats
              </button>
            </li>
            <li role="none">
              <button role="menuitem" type="button" onclick={() => game.openView('privacy')}>
                Privacy
              </button>
            </li>
          </ul>
        {/if}
      </div>
    </div>
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
      {#if hole.start.shortDesc || hole.target.shortDesc}
        <dl class="route-desc">
          {#if hole.start.shortDesc}
            <div>
              <dt>From</dt>
              <dd>{hole.start.shortDesc}</dd>
            </div>
          {/if}
          {#if hole.target.shortDesc}
            <div>
              <dt>To</dt>
              <dd>{hole.target.shortDesc}</dd>
            </div>
          {/if}
        </dl>
      {/if}
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
  .topbar-actions {
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .menu-wrap {
    position: relative;
  }
  .menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 5;
  }
  .menu {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    z-index: 6;
    margin: 0;
    padding: 4px;
    list-style: none;
    min-width: 160px;
    background: var(--night);
    border: 2px solid var(--outline);
    box-shadow: var(--frame);
  }
  .menu button {
    width: 100%;
    padding: 10px 12px;
    border: 0;
    background: transparent;
    color: var(--paper);
    font-size: 16px;
    font-weight: 700;
    text-align: left;
    cursor: pointer;
  }
  .menu button:hover {
    background: var(--grass);
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
  .route-desc {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 4px 0 0;
  }
  .route-desc div {
    display: flex;
    gap: 8px;
    font-size: 14px;
    line-height: 1.35;
  }
  .route-desc dt {
    flex: none;
    width: 2.6em;
    font-weight: 700;
    color: var(--mist);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 11px;
    padding-top: 2px;
  }
  .route-desc dd {
    margin: 0;
    color: var(--ink);
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
