-- 1. flight_search_cache: the last successful flight search per route and dates.
--
-- A recent entry is reused instead of calling the paid provider again (saves monthly
-- quota when parties look at the same route), and when every provider fails the last
-- entry is shown, clearly marked with its age, instead of the stage dead-ending.
-- Flights are never invented or estimated: only real provider results are stored.
-- Backend-only (RLS on, no anon policy).
CREATE TABLE IF NOT EXISTS flight_search_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- "origin|destination|depart_after|depart_before", lower-cased; see FlightCacheRepository.
  cache_key TEXT NOT NULL UNIQUE,
  options JSONB NOT NULL,
  currency TEXT NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_flight_search_cache_fetched_at ON flight_search_cache (fetched_at);
ALTER TABLE flight_search_cache ENABLE ROW LEVEL SECURITY;

-- 2. llm_calls: one row per language-model call, with no prompt or answer text.
--
-- Prompts and completions carry party data (names, budgets, dates), so only the shape of
-- each call is kept: which operation, which model answered, how it ended and how long it
-- took. Enough to see reliability and which fallbacks fire, without storing party text.
-- Backend-only. Prune with: DELETE FROM llm_calls WHERE created_at < NOW() - INTERVAL '30 days';
CREATE TABLE IF NOT EXISTS llm_calls (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  operation TEXT NOT NULL,
  model TEXT,
  outcome TEXT NOT NULL CHECK (outcome IN ('ok', 'wrong_shape', 'all_models_failed')),
  latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0)
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created_at ON llm_calls (created_at DESC);
ALTER TABLE llm_calls ENABLE ROW LEVEL SECURITY;
