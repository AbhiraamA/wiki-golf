-- Phase 4: a PII-free throttle for POST /api/restore. One row per time bucket holds an attempt
-- count; no IP or other identifier is stored (the privacy page promises IPs are never kept).
-- The retention cron prunes expired buckets.
CREATE TABLE rate_limits (
  bucket TEXT PRIMARY KEY,
  count INTEGER NOT NULL DEFAULT 0,
  reset_at INTEGER NOT NULL
);
