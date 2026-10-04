# party-lobby

The entry + live waiting room for a party, built on the real backend room
contract (`RoomService` from `@/services`).

## What it does

- **Entry (`PartyLobby`)** — one adventurer-name field plus a room-name + Create
  Party action and a room-code + Join Party action, framed in-world by the NPC
  `DialogueBox`.
- **Pipeline shell (`PartyRoomShell`)** — once in a room, wraps the experience
  in the honest six-stage stepper (`StageStepper`) derived from
  `room.planningStage`. The SETUP stage renders the real content
  (`SetupStageContent`: room code share + live `RosterPanel`); every later stage
  (discover/logistics/build/refine/wrap) renders an honest `StagePlaceholder`
  with no fake data and no service calls, because those backends do not exist.
- **Waiting room (`PartyWaitingRoom`)** — standalone page chrome (title + leave)
  around `SetupStageContent`; kept for reuse/tests. The shell renders the same
  setup content inside the pipeline.
- **`LobbyApp`** — the only stateful piece; runs `usePartyLobby` and renders
  entry vs the in-room pipeline shell.

## Key pieces

- `hooks/usePartyLobby.ts` — view state, session, live roster via
  `room.subscribeMembers` while waiting (unsubscribed on cleanup/leave/unmount),
  copy-code, leave, and create/join with safe error mapping. All data access via
  `getServices()`.
- `lib/stages.ts` — the six-stage model: ordered stages, in-world titles/blurbs,
  and `buildStageSteps(planningStage)` to derive complete/current/upcoming.
  `isStageStubbed` marks every stage except SETUP as backend-less.
- `lib/lobbyValidation.ts` — client-side bounds (room name 1–100, display name
  1–50, code non-blank) so invalid input makes no service call.
- `lib/lobbyErrors.ts` — maps `ApiError.code` to safe, player-facing messages.
  UI branches on `code`, never raw messages.

## Conventions / notes

- Shared primitives are imported directly from their files in `@/components`
  (`PixelButton`, `PixelCard`, `DialogueBox`, `CharacterSprite`) rather than a
  copy. The roster and the stage stepper are composed from `PixelCard` because no
  dedicated `PartyRoster`/`ProgressIndicator` primitive file currently exists in
  the shared set.
- Live roster uses `room.subscribeMembers` behind the `RoomService` boundary:
  the mock simulates it with an interval, the real service uses a Supabase
  Realtime channel on `room_members`. The UI never imports the Supabase client
  directly — all Supabase access stays in `src/services/*.api.ts`.
- Stages 2–6 are honest placeholders: their backends (the AI Travel Guide) do
  not exist yet, so they render `StagePlaceholder` with no fake data and make no
  chat/vote/itinerary service calls (those real services throw `notImplemented`).
