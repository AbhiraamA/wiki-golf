<script lang="ts">
  import CloseIcon from '../components/icons/CloseIcon.svelte';
  import ShotList from '../components/ShotList.svelte';
  import type { Game } from '../lib/game.svelte';
  import { copyShare, shareText } from '../lib/share';

  let { game }: { game: Game } = $props();

  const result = $derived(game.result);
  const holed = $derived(result?.holed ?? false);

  const CONFETTI = [
    [30, 20, '#E8452C', 0],
    [70, 60, '#E9C977', 120],
    [110, 10, '#8CCFE0', 240],
    [150, 40, '#F4EBD0', 60],
    [190, 0, '#86C98A', 300],
    [230, 30, '#E8452C', 180],
    [270, 12, '#E9C977', 360],
    [310, 50, '#8CCFE0', 90],
    [350, 24, '#86C98A', 210],
    [50, 90, '#F4EBD0', 420],
    [200, 80, '#E9C977', 480],
    [330, 100, '#E8452C', 540],
  ] as const;

  let showScorecard = $state(false);
  let shareLabel = $state('SHARE RESULT');

  function mmss(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  const rarityLine = $derived(
    result?.rarity === 'pending' || result?.rarity == null
      ? 'Rarity shows once 100 players have finished today.'
      : `Rarer than ${result.rarity}% of today’s finishers.`,
  );

  async function share() {
    if (!game.hole || !result) return;
    const text = shareText(
      game.hole.holeNo,
      result.word ?? '',
      result.strokes ?? 0,
      result.par ?? 0,
      game.shots,
    );
    shareLabel = (await copyShare(text)) ? 'COPIED!' : 'COPY BLOCKED HERE';
  }
</script>

{#if result}
  <div class="holed" role="dialog" aria-modal="true" aria-label="Round complete">
    <div class="holed-inner">
      {#if holed}
        <div class="confetti" aria-hidden="true">
          {#each CONFETTI as c, i (i)}
            <span
              style={`left:${c[0]}px;top:${c[1]}px;background:${c[2]};animation-delay:${c[3]}ms`}
            ></span>
          {/each}
        </div>
      {/if}

      <div class="holed-head">
        <span
          >Hole {game.hole?.holeNo} · Par {game.hole?.par}{game.practice ? ' · Practice' : ''}</span
        >
        <button
          class="icon-btn"
          type="button"
          aria-label="Back to the tee"
          onclick={() => game.backToTee()}
        >
          <CloseIcon />
        </button>
      </div>

      <div class="cup" aria-hidden="true">
        <svg class="px" width="90" height="70" viewBox="0 0 18 14">
          <rect x="1" y="11" width="16" height="3" fill="#B4E08A" /><rect
            x="0"
            y="12"
            width="18"
            height="1"
            fill="#B4E08A"
          />
          <rect x="7" y="11" width="4" height="1" fill="#142019" /><rect
            x="9"
            y="0"
            width="1"
            height="11"
            fill="#142019"
          />
          <rect x="10" y="0" width="6" height="1" fill="#E8452C" /><rect
            x="10"
            y="1"
            width="5"
            height="1"
            fill="#E8452C"
          />
          <rect x="10" y="2" width="3" height="1" fill="#E8452C" /><rect
            x="10"
            y="3"
            width="1"
            height="1"
            fill="#E8452C"
          />
        </svg>
        {#if holed}<span class="dropball"></span>{/if}
      </div>

      <h2 class="result-word">{result.word}</h2>
      <p class="result-sub">
        {result.strokes} strokes on a par {result.par} · {mmss(result.seconds ?? 0)}
      </p>

      <div
        class="squares"
        role="img"
        aria-label={`Your round: ${game.shots.map((s) => s.lie).join(', ')}`}
      >
        {#each game.shots as shot, i (i)}
          <span class="sq-{shot.lie}"></span>
        {/each}
      </div>

      <p class="holed-note">{rarityLine}</p>

      {#if showScorecard}
        <section class="scorecard" aria-label="Scorecard">
          <ShotList shots={game.shots} />
        </section>
      {/if}

      <div class="holed-actions">
        <button class="btn-primary" type="button" onclick={share}>{shareLabel}</button>
        <div class="two-up">
          <button
            class="btn-ghost"
            type="button"
            aria-expanded={showScorecard}
            onclick={() => (showScorecard = !showScorecard)}
          >
            {showScorecard ? 'Hide card' : 'Scorecard'}
          </button>
          <button class="btn-ghost" type="button" onclick={() => game.teeOff(true)}
            >Play again</button
          >
        </div>
      </div>
    </div>
  </div>
{/if}
