<script lang="ts">
  import type { Snippet } from 'svelte';
  import CloseIcon from './icons/CloseIcon.svelte';

  interface Props {
    title: string;
    onclose: () => void;
    children: Snippet;
  }

  let { title, onclose, children }: Props = $props();

  const titleId = $props.id();
  let closeBtn: HTMLButtonElement | undefined = $state();

  $effect(() => {
    const previous = document.activeElement as HTMLElement | null;
    closeBtn?.focus();
    return () => previous?.focus();
  });

  function onkeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onclose();
  }

  function onBackdrop(e: MouseEvent) {
    if (e.target === e.currentTarget) onclose();
  }
</script>

<svelte:window {onkeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onBackdrop}>
  <div class="sheet" role="dialog" aria-modal="true" aria-labelledby={titleId}>
    <div class="sheet-head">
      <h2 id={titleId}>{title}</h2>
      <button
        class="icon-btn"
        type="button"
        aria-label="Close"
        bind:this={closeBtn}
        onclick={onclose}
      >
        <CloseIcon />
      </button>
    </div>
    {@render children()}
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 20;
    background: rgba(8, 20, 14, 0.62);
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
  }
  .sheet {
    width: 100%;
    max-width: 560px;
    margin: 0 auto;
    max-height: 78%;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px 16px 28px;
    background: var(--paper);
    color: var(--ink);
    box-shadow: 0 -4px 0 0 var(--shadow);
    overflow-y: auto;
  }
  .sheet-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-left: 4px;
  }
  .sheet-head h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 24px;
    font-weight: 700;
  }
  .sheet .icon-btn {
    color: var(--ink);
  }
</style>
