<script lang="ts">
  import type { Game, TagKind } from '../lib/game.svelte';
  import BallIcon from './icons/BallIcon.svelte';
  import FlagIcon from './icons/FlagIcon.svelte';

  let { game }: { game: Game } = $props();

  const TAG_TEXT: Record<string, string> = {
    fairway: 'FAIRWAY!',
    rough: 'ROUGH',
    bunker: 'BUNKER!',
    mulligan: 'MULLIGAN',
    caddie: 'CADDIE +1',
  };

  // Ball position along the strip, from the tee (far) to the pin (near).
  const ballPct = $derived(Math.max(0, 2 + ((game.maxDist - game.toPin) / game.maxDist) * 86));
  const tagPct = $derived(Math.min(76, Math.max(14, ballPct)));

  const tagKind = $derived<TagKind | 'start' | 'dist'>(
    game.event ?? (game.strokes === 0 && game.shots.length === 0 ? 'start' : 'dist'),
  );
  const tagText = $derived(
    tagKind === 'start'
      ? 'TAP A LINK'
      : tagKind === 'dist'
        ? `${game.toPin} TO PIN`
        : (TAG_TEXT[tagKind] ?? `${game.toPin} TO PIN`),
  );
  const tagData = $derived(
    tagKind === 'fairway' || tagKind === 'rough' || tagKind === 'bunker' || tagKind === 'caddie'
      ? tagKind
      : 'dist',
  );
</script>

<header class="course-head">
  <div class="course-meta">
    <span class="left">
      <span>Hole {game.hole?.holeNo} · Par {game.hole?.par}</span>
      {#if game.practice}<span class="practice-chip">PRACTICE</span>{/if}
    </span>
    <span>Stroke {game.strokes + 1}</span>
  </div>

  <div
    class="course"
    role="img"
    aria-label={`Your ball is ${game.toPin} links from the pin at ${game.hole?.target.title.replace(/_/g, ' ')}`}
    style={`--ball:${ballPct.toFixed(1)}%;--tag:${tagPct.toFixed(1)}%`}
  >
    <div class="band"></div>
    <div class="greenpatch"></div>
    <div class="teebox"></div>
    <FlagIcon />
    <BallIcon />
    {#key game.event}
      <div class="tag-wrap">
        <span class="tag anim-pop" data-kind={tagData} role="status" aria-live="polite"
          >{tagText}</span
        >
      </div>
    {/key}
    <span class="end">{game.hole?.start.title.replace(/_/g, ' ')}</span>
    <span class="end right">{game.hole?.target.title.replace(/_/g, ' ')}</span>
  </div>

  {#if game.hole?.target.shortDesc}
    <p class="pin-desc">
      <span class="pin-label">Pin</span>
      {game.hole.target.shortDesc}
    </p>
  {/if}
</header>

<style>
  .pin-desc {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin: 6px 0 0;
    font-size: 13px;
    line-height: 1.3;
    color: var(--mist);
  }
  .pin-label {
    flex: none;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 11px;
    color: var(--ink);
  }
</style>
