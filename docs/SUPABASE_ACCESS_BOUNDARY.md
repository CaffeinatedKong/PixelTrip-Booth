# Supabase Access Boundary

Which side talks to Supabase, and for what. **FastAPI is the source of truth for all
business logic.** Supabase provides storage, Realtime, and infrastructure. It does not
replace the backend service layer.

The canonical rules live in
[`supabase-architecture.md`](../.kiro/steering/supabase-architecture.md) and Requirement 23
of the [backend core spec](../.kiro/specs/02-backend-core/requirements.md). This page is the
quick reference.

## Writes go through FastAPI

The frontend must call the FastAPI API for these operations. Direct Supabase writes from
the frontend are not allowed.

| Operation | FastAPI endpoint |
|---|---|
| Create room | `POST /rooms` |
| Join or resume a room | `POST /rooms/{room_code}/join` |
| Update preferences | future endpoint |
| Submit vote | future endpoint |
| Generate itinerary | future endpoint |
| Refine itinerary | future endpoint |
| Update planning state | future endpoint |

Only the backend repository layer (`backend/app/repositories/`) writes to the core tables:
`party_rooms`, `guests`, `room_members`, `characters`, and `travel_preferences`.

**New mutations default to FastAPI.** A direct frontend write needs an explicit
justification, documented in the spec that introduces it.

## What the frontend may do directly

Using the **anon key only**, the frontend may:

1. **Subscribe to Realtime** changes on `room_members`, `messages`, `vote_sessions`,
   `votes`, `selections`, `itinerary_versions`, `feedback`, `party_rooms.planning_stage`,
   and `trips.status`.
2. **Run non-sensitive reads** on data that is already visible within the room, where no
   business side effect is possible.

Every direct access must be documented with a comment in the relevant
`frontend/src/services/*.ts` file, stating:

- which table is accessed,
- why direct access is appropriate (Realtime or read-only), and
- the expected data shape.

**Realtime timing:** after `channel.subscribe()` reports `SUBSCRIBED`, Supabase takes a
moment more before database changes are delivered (it then sends a `system` message,
"Subscribed to PostgreSQL"). Changes made in that gap are missed. So subscribe first,
wait for that system message, then load the initial data (e.g. `listMembers`) — that way
nothing falls between the initial load and the live updates.

Example:

```ts
// Direct Supabase access (approved: Realtime, read-only).
// Table: room_members — live party roster for the current room.
// Shape: { id, room_id, guest_id, display_name, role, created_at }
```

> **Current state:** the anon key can read `party_rooms`, `room_members`, `guests`, and
> `characters` (migration `20260926000000_anon_room_read_policies.sql`). Every other table,
> including `travel_preferences`, returns no rows to the anon key until a policy is added
> for it. The anon key cannot write to the core tables at all.

## Keys

| Key | Where it lives | Used for |
|---|---|---|
| Service-role key | `backend/.env` only (`SUPABASE_SERVICE_ROLE_KEY`) | All backend reads and writes. Bypasses RLS. |
| Anon key | Frontend environment | Approved direct reads and Realtime only. |

The service-role key must never be shipped to, bundled with, or logged by the frontend.
The backend never returns it in a response; error responses use the standard
`{"error": {"code", "message"}}` envelope with safe messages only.
