---
inclusion: fileMatch
fileMatchPattern: '{supabase,src/services,src/lib,db,migrations}/**'
---

# Supabase Architecture

Supabase is the frontend-owned data platform: PostgreSQL, Realtime, Storage, and Row Level
Security. **Supabase Auth is not used** — there is no sign-up / sign-in. Users are guests
identified by a display name and a client-generated session id.

## Supabase Responsibilities

- **Guest identity** — lightweight guest profile (display name + session id). No passwords,
  no email, no Supabase Auth.
- **Guest profiles** — the guest's display name and avatar reference.
- **Pixel characters** — avatar and appearance selections per user.
- **Travel preferences** — dates, destinations, style, budget, interests, activities.
- **Party rooms** — shared planning rooms.
- **Members** — room membership (which users are in which room).
- **Messages** — chat messages (user and AI/NPC) within a room.
- **Votes** — votes cast against decision options (destination in DISCOVER, flight in
  LOGISTICS).
- **Selections** — the party's locked-in destination and flight/travel choice.
- **Itineraries & versions** — the generated plan and each revised version from REFINE.
- **Feedback** — comments and suggested changes the party raises during REFINE.
- **Stage & state** — the active stage and application-state progress (see
  `system-workflow.md`).
- **Realtime updates** — live sync of messages, members, votes, itinerary versions,
  feedback, and planning progress.
- **Storage** — sprite assets and any uploaded imagery.

## Recommended Database Entities

Names are recommendations; keep them stable once agreed. All tables use a UUID primary
key and `created_at` / `updated_at` timestamps unless noted.

- **guests** — `id` (client-generated UUID), `display_name`, `avatar_url`. Represents a
  guest user; not backed by Supabase Auth. Referred to as the "user" elsewhere.
- **characters** — `id`, `guest_id → guests.id`, `appearance` (jsonb), `sprite_key`.
- **travel_preferences** — `id`, `character_id → characters.id`, `available_dates`,
  `destinations`, `travel_style`, `budget`, `interests`, `activities`.
- **party_rooms** — `id`, `name`, `owner_id → guests.id`, `status`, `planning_stage`.
- **room_members** — `id`, `room_id → party_rooms.id`, `guest_id → guests.id`,
  `character_id → characters.id`, `role`. Unique on (`room_id`, `guest_id`).
- **messages** — `id`, `room_id → party_rooms.id`, `sender_type` (`user` | `ai`),
  `sender_id` (guest id; nullable for AI), `kind`
  (`text` | `recommendation` | `vote` | `summary`), `content` (jsonb).
- **vote_sessions** — `id`, `room_id → party_rooms.id`, `message_id → messages.id`,
  `question`, `options` (jsonb), `status` (`open` | `closed`).
- **votes** — `id`, `vote_session_id → vote_sessions.id`, `guest_id → guests.id`,
  `option_id`. Unique on (`vote_session_id`, `guest_id`).
- **selections** — `id`, `room_id → party_rooms.id`, `kind` (`destination` | `flight`),
  `data` (jsonb), `vote_session_id → vote_sessions.id`. The locked-in choice per decision.
- **trips** — `id`, `room_id → party_rooms.id`, `title`, `summary`, `status`
  (drives the application states). The trip header; the plan itself lives in
  `itinerary_versions`.
- **itinerary_versions** — `id`, `trip_id → trips.id`, `version` (int), `itinerary`
  (jsonb), `is_current` (bool), `source` (`build` | `refine`). Version 1 comes from BUILD;
  REFINE appends new versions. One current version per trip.
- **feedback** — `id`, `trip_id → trips.id`, `version → itinerary_versions.version`,
  `guest_id → guests.id`, `target` (section reference), `comment`, `status`
  (`open` | `addressed`). Raised during REFINE.

Stage/state note: `party_rooms.planning_stage` holds the active stage; `trips.status`
tracks the application-state progression (see `system-workflow.md`).

## Relationships (summary)

- `guests 1—N characters`
- `characters 1—1 travel_preferences`
- `guests 1—N party_rooms` (owner)
- `party_rooms 1—N room_members`, `party_rooms 1—N messages`, `party_rooms 1—N vote_sessions`
- `vote_sessions 1—N votes`
- `party_rooms 1—N selections` (destination + flight)
- `party_rooms 1—1 trips` (one active trip per room)
- `trips 1—N itinerary_versions`, `trips 1—N feedback`

## Row Level Security

Because there is no Supabase Auth, RLS cannot key off `auth.uid()`. Treat this as a
**guest / demo trust model**, not authenticated per-user security:
- RLS is still enabled on every table; the client uses the anon key with policies scoped
  to the app's needs (e.g. row access constrained by `room_id` / `guest_id` passed by the
  client), accepting that guest identity is self-asserted.
- Do not store sensitive personal data — guests provide only a display name.
- AI-authored messages are written via a trusted backend role (service key), not the
  client.
- If real per-user security is needed later, introduce Supabase Auth and revisit these
  policies. Documented here so the tradeoff is explicit.

## Realtime

- Subscribe per room. Recommended channel key: `room:{room_id}`.
- Realtime-tracked tables: `messages`, `room_members`, `votes`, `vote_sessions`,
  `selections`, `itinerary_versions`, `feedback`, and `party_rooms.planning_stage` /
  `trips.status`.
- Presence (who is online in the room) uses Supabase Realtime presence.

## Storage

- Bucket for pixel/sprite assets and any user uploads.
- Reference stored objects by key/URL from `characters.sprite_key` / `guests.avatar_url`.

## Access Rules

Only the service layer (`src/services`) and the Supabase client in `src/lib` touch
Supabase. UI components never query Supabase directly. See `frontend-architecture.md`.
