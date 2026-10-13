-- Hand-written destination guides: what the AI guide falls back on when the language
-- model is unavailable, and what DISCOVER/BUILD use for places it has no answer for.
--
-- Editing a row here changes the next run: no deploy needed. Backend-only (RLS on, no
-- anon policy), read through the service role like agent_runs. Nothing LLM-written is ever
-- stored here: a cached model answer would carry one party's names and dates into another
-- party's trip, so these are authored by hand.
--
-- The seed rows are in 20261014000003_destination_guides_seed.sql, generated from
-- backend/app/agents/data/destination_guides.json by backend/scripts/export_guides_seed.py.
CREATE TABLE IF NOT EXISTS destination_guides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- "City, Country", the same form the vote options and itineraries use.
  name TEXT NOT NULL UNIQUE CHECK (name ~ '^[^,]{2,},[^,]{2,}$' AND char_length(name) <= 80),
  -- Region / vibe words the party's preferences are matched against ("asia", "beach").
  keywords TEXT[] NOT NULL DEFAULT '{}',
  description TEXT NOT NULL CHECK (char_length(btrim(description)) > 0),
  details TEXT NOT NULL DEFAULT '',
  tags TEXT[] NOT NULL DEFAULT '{}',
  -- Rough SGD per person per day for stay, food and local transport (no flights).
  daily_cost_sgd INTEGER NOT NULL CHECK (daily_cost_sgd > 0),
  typical_days INTEGER NOT NULL CHECK (typical_days BETWEEN 1 AND 30),
  -- Offered as a DISCOVER suggestion; false = only used to plan a trip to it.
  suggest BOOLEAN NOT NULL DEFAULT TRUE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS destination_activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  guide_id UUID NOT NULL REFERENCES destination_guides(id) ON DELETE CASCADE,
  -- Authoring order; ties in the party's interests are broken by it.
  sort_order INTEGER NOT NULL CHECK (sort_order >= 0),
  title TEXT NOT NULL CHECK (char_length(btrim(title)) BETWEEN 1 AND 120),
  slot TEXT NOT NULL CHECK (slot IN ('morning', 'afternoon', 'evening')),
  -- 24-hour HH:MM; null = the slot's default time.
  start_time TEXT CHECK (start_time IS NULL OR start_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'),
  description TEXT NOT NULL DEFAULT '',
  location TEXT NOT NULL DEFAULT '',
  -- Rough SGD per person; 0 = free.
  cost_sgd NUMERIC(8, 2) NOT NULL DEFAULT 0 CHECK (cost_sgd >= 0),
  tags TEXT[] NOT NULL DEFAULT '{}',
  UNIQUE (guide_id, sort_order)
);

ALTER TABLE destination_guides ENABLE ROW LEVEL SECURITY;
ALTER TABLE destination_activities ENABLE ROW LEVEL SECURITY;
