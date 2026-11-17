<script lang="ts">
  import { placeholderHole } from './lib/placeholder';
  import Tee from './screens/Tee.svelte';

  // Phase 0: tee screen only, with a sample hole. Play, API and storage arrive in later phases.
  const hole = placeholderHole();
</script>

<Tee {hole} streak={0} onteeoff={() => {}} />
