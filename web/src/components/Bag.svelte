<script lang="ts">
  import type { Game } from '../lib/game.svelte';

  let { game }: { game: Game } = $props();

  const canMulligan = $derived(game.mulliganLeft && game.shots.length > 0 && !game.busy);
  const mulliganNote = $derived(
    !game.mulliganLeft ? 'Used' : game.shots.length === 0 ? 'No shot yet' : '1 left',
  );
</script>

<button
  type="button"
  class="bag-item"
  aria-disabled={!canMulligan}
  onclick={() => canMulligan && game.mulligan()}
>
  <svg class="px" width="22" height="22" viewBox="0 0 10 10" aria-hidden="true" fill="currentColor">
    <rect x="2" y="1" width="1" height="1" /><rect x="1" y="2" width="1" height="1" /><rect
      x="0"
      y="3"
      width="7"
      height="1"
    />
    <rect x="1" y="4" width="1" height="1" /><rect x="2" y="5" width="1" height="1" /><rect
      x="7"
      y="4"
      width="1"
      height="1"
    />
    <rect x="8" y="5" width="1" height="2" /><rect x="7" y="7" width="1" height="1" /><rect
      x="3"
      y="8"
      width="4"
      height="1"
    />
  </svg>
  <span class="txt"
    ><span class="name">Mulligan</span><span class="sub">Undo your last shot</span></span
  >
  <span class="meta">{mulliganNote}</span>
</button>

<button
  type="button"
  class="bag-item"
  aria-disabled={game.busy}
  onclick={() => !game.busy && game.caddie()}
>
  <svg class="px" width="22" height="22" viewBox="0 0 10 10" aria-hidden="true" fill="currentColor">
    <rect x="3" y="0" width="4" height="1" /><rect x="2" y="1" width="1" height="1" /><rect
      x="7"
      y="1"
      width="1"
      height="1"
    />
    <rect x="1" y="2" width="1" height="3" /><rect x="8" y="2" width="1" height="3" /><rect
      x="2"
      y="5"
      width="1"
      height="1"
    />
    <rect x="7" y="5" width="1" height="1" /><rect x="3" y="6" width="1" height="1" /><rect
      x="6"
      y="6"
      width="1"
      height="1"
    />
    <rect x="3" y="7" width="4" height="1" /><rect x="3" y="9" width="4" height="1" />
  </svg>
  <span class="txt"
    ><span class="name">Ask the caddie</span><span class="sub"
      >Highlights a link that gets closer</span
    ></span
  >
  <span class="meta">+1</span>
</button>
