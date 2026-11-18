<script lang="ts">
  import { Game } from './lib/game.svelte';
  import Holed from './screens/Holed.svelte';
  import Play from './screens/Play.svelte';
  import Tee from './screens/Tee.svelte';

  const game = new Game();

  // Dev-only (mock build): ?auto=play|holed drives the game for screenshots. Tree-shaken in prod.
  const auto = import.meta.env.VITE_MOCK ? new URLSearchParams(location.search).get('auto') : null;
  if (auto === 'play' || auto === 'holed') {
    void game.autoplay(auto);
  } else {
    void game.init();
  }
</script>

<main>
  {#if game.screen === 'tee'}
    <Tee {game} />
  {:else if game.screen === 'play'}
    <Play {game} />
  {/if}
</main>

{#if game.screen === 'holed'}
  <Holed {game} />
{/if}

<style>
  main {
    display: contents;
  }
</style>
