/**
 * Feature-local mock fixtures for the adventure sidebar.
 *
 * UI-only placeholders consumed directly by the Lobby / Character Creation feature.
 * This is NOT a backend contract and NOT a service: it imports nothing from
 * `src/mocks` or `src/services` (no `*.mock.ts` / `*.api.ts`). Nothing here is
 * persisted or sent anywhere — the feature is frontend-only and session-only.
 *
 * When a real room/party service lands, these fixtures can be replaced by data
 * mapped from `api-contracts.md`-shaped responses.
 */

import { deriveBudgetView } from "./budget";
import type { RoomMember } from "@/types";
import type { AdventureView, PartyMemberView } from "../types";

/** The mock party already seated in the room. */
const MOCK_PARTY_MEMBERS: readonly PartyMemberView[] = [
  {
    id: "member-keith",
    displayName: "Explorer Keith",
    archetypeLabel: "Explorer",
    spriteKey: "explorer-01",
  },
  {
    id: "member-alice",
    displayName: "Ranger Alice",
    archetypeLabel: "Ranger",
    spriteKey: "ranger-01",
  },
  {
    id: "member-bob",
    displayName: "Scholar Bob",
    archetypeLabel: "Scholar",
    spriteKey: "scholar-01",
  },
] as const;

/** The feature-local adventure sidebar view model fixture. */
export const MOCK_ADVENTURE_VIEW: AdventureView = {
  tripName: "JAPAN ADVENTURE",
  dateRangeLabel: "12 Dec → 20 Dec",
  members: MOCK_PARTY_MEMBERS,
  capacity: 4,
  budget: deriveBudgetView(1500, 0),
};


/**
 * Capacity shown in the party panel. Not a backend-enforced limit — a display
 * hint for how many empty slots to render alongside the real roster.
 */
export const DEFAULT_PARTY_CAPACITY = 4;

/** Map a live room member into the sidebar's party-member view model. */
function toPartyMemberView(member: RoomMember): PartyMemberView {
  return {
    id: member.id,
    displayName: member.displayName,
    // No archetype is persisted yet (character creation is session-only), so we
    // label by role until a real character record exists.
    archetypeLabel: member.role === "owner" ? "Host" : "Member",
    // The guest id doubles as a stable sprite key placeholder.
    spriteKey: member.guestId,
  };
}

/**
 * Build the adventure sidebar view model from the LIVE party roster.
 *
 * Trip name, date label, and budget remain feature-local placeholders (no trip
 * backend yet), but the party members come straight from the real room roster so
 * the PARTY panel reflects who is actually in the room. Capacity grows if the
 * party already exceeds {@link DEFAULT_PARTY_CAPACITY} so no member is hidden.
 */
export function buildAdventureView(
  members: readonly RoomMember[],
): AdventureView {
  return {
    tripName: "JAPAN ADVENTURE",
    dateRangeLabel: "12 Dec → 20 Dec",
    members: members.map(toPartyMemberView),
    capacity: Math.max(DEFAULT_PARTY_CAPACITY, members.length),
    budget: deriveBudgetView(1500, 0),
  };
}
