---
inclusion: fileMatch
fileMatchPattern: '{src/services,src/types,app/api}/**'
---

# API Contracts

Defines what the frontend expects from the backend. These shapes are the shared contract
that both sides build against: the frontend service layer consumes them and the backend
produces them. Frontend and backend are developed in parallel, so this contract is the
integration point. Treat these as agreed shapes; changes must be coordinated across both
teams.

Notes:
- Data persistence runs through Supabase (no Supabase Auth). AI orchestration runs through
  the FastAPI + LangGraph backend. The frontend does not care which is which beyond the
  service interface.
- All shapes below are conceptual (field lists), not implementation code. IDs are UUID
  strings; timestamps are ISO 8601 strings.

## Guest Identity Flow (No Auth)

There is no sign-up / sign-in. Identity is a lightweight guest.
- The client creates a guest with a display name → `{ id, displayName, avatarUrl? }`.
- The guest id is a client-generated UUID, persisted locally (e.g. session/local storage)
  so the guest survives reloads within the session.
- All subsequent calls carry the guest id; there are no tokens, passwords, or auth errors.
- "User" in the shapes below means this guest.

## Chat Message Flow

A room message has a stable envelope:
- `id`, `roomId`, `createdAt`
- `senderType`: `"user" | "ai"`
- `senderId`: user id, or null for AI
- `kind`: `"text" | "recommendation" | "vote" | "summary"`
- `content`: shape depends on `kind` (see below)

Flow:
1. User sends a text message → persisted to Supabase → broadcast via Realtime.
2. Backend AI produces messages (any `kind`) → persisted → broadcast via Realtime.
3. Clients render new messages from the Realtime stream.

## AI Response Structure

An AI turn returns one or more messages sharing the envelope above. Common fields in
`content` for AI text:
- `text`: NPC dialogue string.
- `options?`: array of `{ id, label }` for quick single-choice replies.
- `stage?`: current planning stage indicator (drives progress UI).

## Recommendation Response Structure

`kind: "recommendation"` content. Used in DISCOVER (destinations) and LOGISTICS (flights):
- `title`: short heading.
- `category?`: `"destination" | "flight"` — which stage this set belongs to.
- `items`: array of recommendation entries, each:
  - `id`, `title`, `description`
  - `imageUrl?` / `spriteKey?`
  - `meta?`: key/value details for comparison (e.g. price band, duration, tags).
    For flights this carries the comparable fields (price, airline, duration, stops,
    depart/return times); for destinations, things like region, budget band, highlights.
- `prompt?`: optional follow-up question for the party.

The frontend renders destination and flight option sets with the same recommendation +
comparison UI, keyed off `category`.

## Voting Structure

Voting has a session plus per-user votes.

Vote session (`kind: "vote"` content or dedicated object):
- `voteSessionId`, `roomId`, `question`
- `options`: array of `{ id, label, count }`
- `status`: `"open" | "closed"`

Cast a vote:
- Input: `{ voteSessionId, optionId }` (acting user inferred from session).
- One vote per user per session; re-voting replaces the previous choice.
- Live counts update via Realtime.

## Itinerary Format

The trip plan (rendered as quest log in BUILD/REFINE and adventure summary in WRAP). An
itinerary object:
- `tripId`, `roomId`, `title`, `summary`
- `destination`: `{ name, country? }`
- `dates?`: `{ start, end }`
- `days`: array of day plans, each:
  - `day`: number
  - `date?`
  - `items`: ordered activities, each `{ time?, title, description?, location?, tags? }`
- `map?`: points array `{ label, lat, lng }` for the travel map view.

The journal, quest log, timeline, and map are all derived from this single object.

## Itinerary Versioning

BUILD produces version 1; REFINE appends new versions. A version wraps the itinerary:
- `version`: incrementing integer.
- `source`: `"build" | "refine"`.
- `isCurrent`: boolean — the version currently shown/approved.
- `itinerary`: the itinerary object above.
- `changeSummary?`: short note of what changed vs. the prior version (REFINE only).

The UI can list versions and step through/compare them; only one is current.

## Feedback & Refinement (REFINE)

Feedback entry (submitted by the party):
- Input: `{ tripId, version, target, comment }`
  - `target`: section reference the feedback applies to (e.g. a day or item id/label).
  - `comment`: the party member's comment or suggested change.
- `status`: `"open" | "addressed"`.

Refinement result (from the AI):
- An analysis `text`/`summary` message: conflicts identified and compromises proposed.
- A new itinerary version (see above) with `source: "refine"` and a `changeSummary`.
- Approval: `{ tripId, version, decision: "approve" }` locks the version and advances
  toward WRAP.

## Stage & State

Every planning surface reflects where the party is:
- `stage`: `"setup" | "discover" | "logistics" | "build" | "refine" | "wrap"` — the active
  stage (also carried on AI `text` content).
- `state`: the application-state progression (see `system-workflow.md`) that gates
  transitions and drives progress UI.

## Export (WRAP)

Finalisation returns:
- The approved itinerary (current version).
- `export`: a shareable payload the WRAP UI offers to share/download.
