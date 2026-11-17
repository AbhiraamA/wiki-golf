<script lang="ts">
  import type { Game } from '../lib/game.svelte';

  let { game, autofocus = false }: { game: Game; autofocus?: boolean } = $props();

  let query = $state('');
  let input: HTMLInputElement | undefined = $state();

  const links = $derived(game.article?.allLinks ?? []);
  const matches = $derived(
    links.filter((t) => {
      const q = query.trim().toLowerCase();
      return !q || t.replace(/_/g, ' ').toLowerCase().includes(q);
    }),
  );

  $effect(() => {
    if (autofocus) input?.focus();
  });
</script>

<label class="panel-title" for="find-input">Find a link</label>
<input
  bind:this={input}
  id="find-input"
  class="input"
  type="search"
  placeholder="Type part of a name"
  autocomplete="off"
  bind:value={query}
/>
<div class="results">
  {#if matches.length === 0}
    <p class="empty">No links on this page match.</p>
  {:else}
    {#each matches as t (t)}
      <button type="button" class="result" disabled={game.busy} onclick={() => game.playLink(t)}>
        {t.replace(/_/g, ' ')}
      </button>
    {/each}
  {/if}
</div>
