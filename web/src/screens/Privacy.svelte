<script lang="ts">
  import { APP_VERSION, CONTACT_EMAIL } from '@wiki-golf/shared';
  import type { Game } from '../lib/game.svelte';

  let { game }: { game: Game } = $props();

  const rows = [
    ['Random player ID', 'Signed cookie, and the server', 'Until you clear it'],
    ['Today’s result and history', 'Your browser only', 'Until you clear it'],
    [
      'Rounds: hole, route, strokes, time',
      'Server, keyed by the random ID',
      '30 days, then totals only',
    ],
    ['Streak summary', 'Server, keyed by the random ID', 'Deleted after 12 months idle'],
    ['Page visit counts', 'Server, no ID attached', 'Kept'],
    ['Names, emails, IP addresses', 'Not stored', '—'],
  ];
</script>

<section class="screen subpage" aria-labelledby="pv-title">
  <header class="subbar">
    <button class="btn-ghost back" type="button" onclick={() => game.closeView()}>← Back</button>
    <h1 id="pv-title">Privacy</h1>
  </header>

  <div class="subbody">
    <p class="lede">
      Wiki Golf is a small game. It keeps as little about you as it can, and never sells or shares
      anything. No ads, no third-party trackers, no analytics cookies.
    </p>

    <h2>What’s stored</h2>
    <table>
      <thead>
        <tr><th>Data</th><th>Where</th><th>Kept for</th></tr>
      </thead>
      <tbody>
        {#each rows as [data, where, kept] (data)}
          <tr><td>{data}</td><td>{where}</td><td>{kept}</td></tr>
        {/each}
      </tbody>
    </table>

    <h2>Your random ID</h2>
    <p>
      When you first tee off we create a random ID and store it in a signed cookie. It isn’t linked
      to your name or email — it only tells the server which anonymous progress is yours. Clear your
      browser data and it’s gone; make a <strong>backup code</strong> on the Stats page first if you want
      to keep your streak.
    </p>

    <h2>Questions</h2>
    <p>Email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>.</p>
    <p class="muted ver">Wiki Golf v{APP_VERSION}</p>
  </div>
</section>

<style>
  .subpage {
    padding: 16px 24px 32px;
  }
  .subbody {
    display: flex;
    flex-direction: column;
    gap: 10px;
    line-height: 1.5;
  }
  .lede {
    margin: 0;
    color: var(--mist);
  }
  a {
    color: var(--green);
  }
  h2 {
    margin: 16px 0 0;
    font-family: var(--font-display);
    font-size: 18px;
    font-weight: 700;
  }
  p {
    margin: 0;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 14px;
  }
  th,
  td {
    border: 2px solid var(--outline);
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
  }
  th {
    background: var(--sand);
    color: var(--ink);
    font-family: var(--font-display);
  }
  .ver {
    margin-top: 16px;
    font-size: 13px;
  }
  @media (min-width: 1024px) {
    .subpage {
      width: 100%;
      max-width: 640px;
      margin: 0 auto;
    }
  }
</style>
