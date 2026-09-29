-- Switch room member identity from normalized name to exact, case-sensitive display name.
-- "Gerald" and "gerald" in the same room become two different members.
-- Adding the new constraint first makes this migration fail (rather than silently drop
-- rows) if duplicate (room_id, display_name) rows already exist.
ALTER TABLE room_members
  ADD CONSTRAINT room_members_room_id_display_name_key UNIQUE (room_id, display_name);

ALTER TABLE room_members
  DROP CONSTRAINT IF EXISTS room_members_room_id_normalized_name_key;

ALTER TABLE room_members
  DROP COLUMN normalized_name;
