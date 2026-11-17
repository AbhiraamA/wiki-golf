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
</header>
