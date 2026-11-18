<script lang="ts">
  import type { Lie } from '@wiki-golf/shared';

  let { shots }: { shots: { lie: Lie; title: string }[] } = $props();

  const WORD: Record<Lie, string> = {
    fairway: 'FAIRWAY',
    rough: 'ROUGH',
    bunker: 'BUNKER',
    holed: 'HOLED',
    out_of_bounds: 'OOB',
  };
</script>

{#if shots.length === 0}
  <p class="empty">No shots yet. Tap a green link in the article.</p>
{:else}
  <ol class="shot-list">
    {#each shots as shot, i (i)}
      <li class="shot">
        <span class="n">{i + 1}</span>
        <span class="t">{shot.title.replace(/_/g, ' ')}</span>
        <span class="lie {shot.lie}">{WORD[shot.lie]}</span>
      </li>
    {/each}
  </ol>
{/if}
