<script lang="ts">
  import { WIKIS } from '@wiki-golf/shared';
  import type { Game } from '../lib/game.svelte';

  let { game }: { game: Game } = $props();

  const article = $derived(game.article);
  const lang = $derived(game.hole ? WIKIS[game.hole.wiki].lang : 'simple');

  // Per-page fold state; reset whenever a new page loads (keyed by pageSeq in the parent).
  let open = $state<Record<string, boolean>>({});

  function titleToLabel(t: string): string {
    return t.replace(/_/g, ' ');
  }

  function play(title: string) {
    void game.playLink(title);
  }
</script>

{#if article}
  {#key game.pageSeq}
    <article
      class="card {game.lastLie === 'bunker' ? 'anim-shake' : 'anim-slide'}"
      aria-live="polite"
    >
      <h1>{titleToLabel(article.title)}</h1>
      {#if article.description}<p class="desc">{article.description}</p>{/if}

      <div class="body">
        {#each article.lead as para (para)}
          <p>
            {#each para as node, i (i)}
              {#if 't' in node}{node.t}{:else}<button
                  type="button"
                  class="wlink"
                  class:hint={node.l === game.hint}
                  class:loading={game.pending === node.l}
                  disabled={game.busy}
                  onpointerenter={() => game.prefetch(node.l)}
                  onfocus={() => game.prefetch(node.l)}
                  onclick={() => play(node.l)}>{node.s}</button
                >{/if}
            {/each}
          </p>
        {/each}
      </div>

      {#each article.sections as section, si (si)}
        <button
          type="button"
          class="fold"
          aria-expanded={open[`s${si}`] ?? false}
          onclick={() => (open = { ...open, [`s${si}`]: !open[`s${si}`] })}
        >
          {open[`s${si}`] ? '−' : '+'}
          {section.heading}
        </button>
        {#if open[`s${si}`]}
          <div class="section-body body">
            {#each section.paras as para (para)}
              <p>
                {#each para as node, i (i)}
                  {#if 't' in node}{node.t}{:else}<button
                      type="button"
                      class="wlink"
                      class:hint={node.l === game.hint}
                      class:loading={game.pending === node.l}
                      disabled={game.busy}
                      onpointerenter={() => game.prefetch(node.l)}
                      onfocus={() => game.prefetch(node.l)}
                      onclick={() => play(node.l)}>{node.s}</button
                    >{/if}
                {/each}
              </p>
            {/each}
          </div>
        {/if}
      {/each}

      {#snippet chipFold(id: string, label: string, links: string[])}
        <button
          type="button"
          class="fold"
          aria-expanded={open[id] ?? false}
          onclick={() => (open = { ...open, [id]: !open[id] })}
        >
          {open[id] ? '−' : '+'}
          {label}
        </button>
        {#if open[id]}
          <div class="chips">
            {#each links as t (t)}
              <button
                type="button"
                class="chip"
                class:loading={game.pending === t}
                disabled={game.busy}
                onpointerenter={() => game.prefetch(t)}
                onfocus={() => game.prefetch(t)}
                onclick={() => play(t)}
              >
                {titleToLabel(t)}
              </button>
            {/each}
          </div>
        {/if}
      {/snippet}

      {#if article.quickFacts.length}{@render chipFold(
          'facts',
          'Quick facts',
          article.quickFacts,
        )}{/if}
      {#if article.moreLinks.length}{@render chipFold('more', 'More links', article.moreLinks)}{/if}
      {@render chipFold(
        'all',
        `All ${article.allLinks.length} links on this page`,
        article.allLinks,
      )}

      <p class="attrib">
        Text:
        <a
          href={`https://${lang}.wikipedia.org/w/index.php?oldid=${game.currentRevId}`}
          target="_blank"
          rel="noreferrer">{titleToLabel(article.title)}</a
        >,
        <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer"
          >CC BY-SA 4.0</a
        >. Shortened and reformatted for Wiki Golf.
      </p>
    </article>
  {/key}
{/if}
