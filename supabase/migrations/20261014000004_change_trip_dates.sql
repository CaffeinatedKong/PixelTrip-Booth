-- Atomic trip-date change, and a guard so a flight cannot be locked from a vote that a
-- date change has closed.
--
-- The backend used to read the destination plan, check that no flight was locked, then
-- write: three separate requests with nothing holding the room still between them, so a
-- flight lock or a second date change could slip in and be overwritten. This function
-- does the whole change in one transaction, holding the room's row so changes in one room
-- queue up.
--
-- Returns a status word instead of raising, so the backend can answer with a precise,
-- user-safe message:
--   ok              the plan was changed
--   no_room         the room does not exist
--   no_destination  no destination has been chosen yet
--   flight_locked   a flight is already locked, so the dates can no longer change
--   changed         the plan is not what the caller read (someone changed it first)
--
-- On success it also closes any open flight vote (it was for the old dates) and resets
-- every member's stage_ready, as the API contract says.
CREATE OR REPLACE FUNCTION change_trip_dates(
  p_room_id UUID,
  p_expected JSONB,  -- {"tripDays":…, "tripStart":…, "tripEnd":…} as the caller read them
  p_data JSONB       -- the destination selection's new data
) RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
  current_data JSONB;
  stale_ids UUID[];
BEGIN
  -- One date change per room at a time.
  PERFORM 1 FROM party_rooms WHERE id = p_room_id FOR UPDATE;
  IF NOT FOUND THEN
    RETURN 'no_room';
  END IF;

  -- Take the open flight vote BEFORE looking for a flight selection. A flight being
  -- locked right now holds a share lock on that vote (see the trigger below), so this
  -- waits for it to commit, and the check that follows then sees the flight it made.
  SELECT COALESCE(array_agg(vs.id), '{}') INTO stale_ids
  FROM (
    SELECT v.id
    FROM vote_sessions v
    JOIN messages m ON m.id = v.message_id
    WHERE v.room_id = p_room_id
      AND v.status = 'open'
      AND m.content ->> 'category' = 'flight'
    FOR UPDATE OF v
  ) vs;

  IF EXISTS (SELECT 1 FROM selections WHERE room_id = p_room_id AND kind = 'flight') THEN
    RETURN 'flight_locked';
  END IF;

  SELECT data INTO current_data
  FROM selections
  WHERE room_id = p_room_id AND kind = 'destination'
  FOR UPDATE;
  IF NOT FOUND THEN
    RETURN 'no_destination';
  END IF;

  -- A missing key and a JSON null mean the same ("no plan yet"); compare them as equal.
  IF (COALESCE(current_data -> 'tripDays', 'null'::JSONB),
      COALESCE(current_data -> 'tripStart', 'null'::JSONB),
      COALESCE(current_data -> 'tripEnd', 'null'::JSONB))
     IS DISTINCT FROM
     (COALESCE(p_expected -> 'tripDays', 'null'::JSONB),
      COALESCE(p_expected -> 'tripStart', 'null'::JSONB),
      COALESCE(p_expected -> 'tripEnd', 'null'::JSONB)) THEN
    RETURN 'changed';
  END IF;

  UPDATE selections
  SET data = p_data, updated_at = NOW()
  WHERE room_id = p_room_id AND kind = 'destination';

  -- The flight vote was for the old dates: clear any tie, then close it.
  UPDATE vote_sessions
  SET tie_pending = FALSE, status = 'closed', updated_at = NOW()
  WHERE id = ANY (stale_ids);

  UPDATE room_members SET stage_ready = FALSE WHERE room_id = p_room_id AND stage_ready;

  RETURN 'ok';
END;
$$;

-- A flight can only be locked from a vote that is still open. Without this, a vote that
-- finished at the same moment as a date change could lock a flight for the old dates
-- after the change had already closed that vote. The share lock makes the check wait for
-- (and then see) any date change in progress.
CREATE OR REPLACE FUNCTION require_open_vote_for_flight()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.kind = 'flight' AND NEW.vote_session_id IS NOT NULL THEN
    PERFORM 1 FROM vote_sessions WHERE id = NEW.vote_session_id AND status = 'open' FOR SHARE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'flight_vote_closed'
        USING DETAIL = 'The flight vote was closed (for example by a date change).';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_selections_require_open_flight_vote ON selections;
CREATE TRIGGER trg_selections_require_open_flight_vote
  BEFORE INSERT OR UPDATE ON selections
  FOR EACH ROW
  EXECUTE FUNCTION require_open_vote_for_flight();
