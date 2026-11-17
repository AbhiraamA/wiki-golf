<script lang="ts">
  import Sheet from './Sheet.svelte';

  let { onclose }: { onclose: () => void } = $props();
</script>

<Sheet title="How to play" {onclose}>
  <div class="how">
    <p>
      Get from the start page to the target page by tapping links in each article. Every tap is one
      stroke.
    </p>
    <p>
      <strong>Fairway</strong> means you got one link closer, <strong>rough</strong> means no
      closer, and <strong>bunker</strong> means farther away.
    </p>
    <p>
      Par is the shortest route plus one. Your bag holds one mulligan (undo a shot) and the caddie
      (a hint for one stroke).
    </p>
  </div>
</Sheet>

<style>
  .how {
    padding: 0 4px;
    font-size: 16px;
    line-height: 1.55;
  }
  .how p {
    margin: 0 0 10px;
  }
  .how p:last-child {
    margin: 0;
  }
</style>
