import { svelte } from '@sveltejs/vite-plugin-svelte';
import { svelteTesting } from '@testing-library/svelte/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [svelte(), svelteTesting()],
  server: {
    port: 5173,
    // In dev the Worker runs separately under `wrangler dev`.
    proxy: { '/api': 'http://localhost:8787' },
  },
  build: { target: 'es2022' },
  test: {
    environment: 'jsdom',
    include: ['test/**/*.test.ts'],
  },
});
