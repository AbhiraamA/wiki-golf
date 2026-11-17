<script lang="ts">
  import { isLongHole, weekday, type HoleInfo } from '@wiki-golf/shared';
  import HowToPlaySheet from '../components/HowToPlaySheet.svelte';
  import TeeArt from '../components/TeeArt.svelte';

  interface Props {
    hole: HoleInfo;
    streak: number;
    onteeoff: () => void;
  }

  let { hole, streak, onteeoff }: Props = $props();

  let howOpen = $state(false);

  const eyebrow = $derived(
    `HOLE ${hole.holeNo} · ${weekday(hole.date).toUpperCase()}${isLongHole(hole.date) ? ' LONG HOLE' : ''}`,
  );
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
      onclick={() => (howOpen = true)}
    >
      ?
    </button>
  </div>

  <TeeArt />

  <div class="tee-info">
    <span class="eyebrow">{eyebrow}</span>
    <h1 class="route-title" id="tee-title">
      {hole.start.title}<br /><span class="to">to</span>
      {hole.target.title}
    </h1>
    <div class="par-row">
      <span class="par-chip">PAR {hole.par}</span>
      <span class="muted">Pick up at {hole.pickUp} strokes</span>
    </div>
  </div>

  <div class="tee-actions">
    <button class="btn-primary" type="button" onclick={onteeoff}>TEE OFF</button>
    <div class="tee-foot"><span>{streakText}</span></div>
  </div>
</section>

{#if howOpen}
  <HowToPlaySheet onclose={() => (howOpen = false)} />
{/if}

<style>
  .screen {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
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
