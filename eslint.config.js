import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';
import ts from 'typescript-eslint';

export default ts.config(
  {
    ignores: [
      '**/dist/',
      '**/.wrangler/',
      '**/node_modules/',
      'design/',
      'worker/worker-configuration.d.ts',
    ],
  },
  js.configs.recommended,
  ...ts.configs.strict,
  ...svelte.configs['flat/recommended'],
  prettier,
  ...svelte.configs['flat/prettier'],
  {
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts'],
    languageOptions: { parserOptions: { parser: ts.parser } },
  },
  {
    rules: {
      // Hard rule 2: never inject Wikipedia HTML.
      'svelte/no-at-html-tags': 'error',
      'no-restricted-properties': [
        'error',
        { property: 'innerHTML', message: 'Build DOM nodes instead (plan.md hard rule 2).' },
        { property: 'outerHTML', message: 'Build DOM nodes instead (plan.md hard rule 2).' },
      ],
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  {
    // Dev-only fixture and tests: controlled data, so non-null assertions are fine.
    files: ['**/*.test.ts', 'web/src/lib/mock.ts'],
    rules: { '@typescript-eslint/no-non-null-assertion': 'off' },
  },
);
