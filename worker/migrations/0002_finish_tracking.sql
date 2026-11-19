-- Phase 4: mark when a finished round's score has been folded into the player's streak,
-- games count and the hole's page-visit tallies, so that re-requests never double-count.
ALTER TABLE rounds ADD COLUMN recorded_at INTEGER;
