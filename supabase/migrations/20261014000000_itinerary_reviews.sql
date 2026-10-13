-- Per-version review consent, and idempotent feedback.
--
-- Until now a member's "approve"/"refine" decision on an itinerary version was not
-- stored, and `room_members.stage_ready` (also set when preferences are saved or a vote
-- is cast) doubled as approval consent. A leftover flag from an earlier stage could make
-- everyone look ready, and "refine" with no feedback rows read as approval.
--
-- itinerary_reviews records one decision per member per version. A new version has no
-- rows, so each review round starts empty. Backend-only, like agent_runs (no anon access).
-- Additive; safe to run on a database that already has itineraries.
CREATE TABLE IF NOT EXISTS itinerary_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
  itinerary_version_id UUID NOT NULL,
  member_id UUID NOT NULL REFERENCES room_members(id) ON DELETE CASCADE,
  decision TEXT NOT NULL CHECK (decision IN ('approve', 'refine')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  FOREIGN KEY (itinerary_version_id, trip_id)
    REFERENCES itinerary_versions(id, trip_id) ON DELETE CASCADE,
  UNIQUE (itinerary_version_id, member_id)
);

ALTER TABLE itinerary_reviews ENABLE ROW LEVEL SECURITY;

-- A retried review submission must not duplicate feedback: one open comment per
-- member, version and target. The backend updates the existing row's comment instead.
CREATE UNIQUE INDEX IF NOT EXISTS uq_feedback_open_member_version_target
  ON feedback (itinerary_version_id, member_id, (target::text))
  WHERE status = 'open';
