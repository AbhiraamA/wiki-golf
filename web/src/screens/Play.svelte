<script lang="ts">
  import ArticleCard from '../components/ArticleCard.svelte';
  import Bag from '../components/Bag.svelte';
  import CourseBar from '../components/CourseBar.svelte';
  import LinkResults from '../components/LinkResults.svelte';
  import Sheet from '../components/Sheet.svelte';
  import ShotList from '../components/ShotList.svelte';
  import BagIcon from '../components/icons/BagIcon.svelte';
  import FindIcon from '../components/icons/FindIcon.svelte';
  import type { Game } from '../lib/game.svelte';

  let { game }: { game: Game } = $props();

  let sheet = $state<'find' | 'bag' | null>(null);

  // Any new page or finish closes the open phone sheet.
  let lastSeq = -1;
  $effect(() => {
    if (game.pageSeq !== lastSeq) {
      lastSeq = game.pageSeq;
      sheet = null;
    }
    if (game.screen !== 'play') sheet = null;
  });
</script>

<section class="screen play" aria-label={`Playing hole ${game.hole?.holeNo}`}>
  <div class="progress" class:on={game.busy} aria-hidden="true"></div>
  <CourseBar {game} />

  <div class="play-body">
    <ArticleCard {game} />
    <div class="dock">
      <button class="find-btn" type="button" onclick={() => (sheet = 'find')}>
        <FindIcon />
        Find a link
      </button>
      <button
        class="bag-btn"
        type="button"
        aria-label="Open your bag: mulligan and caddie"
        onclick={() => (sheet = 'bag')}
      >
        <BagIcon />
      </button>
    </div>
  </div>

  <aside class="aside" aria-label="Tools">
    <section class="panel"><LinkResults {game} /></section>
    <section class="panel">
      <h2 class="panel-title">Your bag</h2>
      <Bag {game} />
    </section>
    <section class="panel">
      <h2 class="panel-title">Shots</h2>
      <ShotList shots={game.shots} />
    </section>
  </aside>
</section>

{#if sheet === 'find'}
  <div class="phone-only">
    <Sheet title="Find a link" onclose={() => (sheet = null)}>
      <LinkResults {game} autofocus />
    </Sheet>
  </div>
{:else if sheet === 'bag'}
  <div class="phone-only">
    <Sheet title="Your bag" onclose={() => (sheet = null)}>
      <Bag {game} />
    </Sheet>
  </div>
{/if}
