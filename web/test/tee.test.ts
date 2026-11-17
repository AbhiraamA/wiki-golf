import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import Tee from '../src/screens/Tee.svelte';
import { placeholderHole } from '../src/lib/placeholder';

describe('Tee screen', () => {
  it('shows the hole, route, par and pick-up', () => {
    const hole = placeholderHole('2026-12-06'); // a Sunday
    render(Tee, { hole, streak: 9, onteeoff: () => {} });
    expect(screen.getByText(/HOLE 6 · SUNDAY LONG HOLE/)).toBeTruthy();
    expect(screen.getByRole('heading', { level: 1 }).textContent).toMatch(
      /Octopus\s*to\s*Apollo 11/,
    );
    expect(screen.getByText('PAR 6')).toBeTruthy();
    expect(screen.getByText('Pick up at 12 strokes')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'TEE OFF' })).toBeTruthy();
    expect(screen.getByText('9-day streak')).toBeTruthy();
  });
});
