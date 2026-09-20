/**
 * Party room and membership shapes plus the planning-stage enum.
 *
 * Mirrors the "Stage & State" and party-room concepts in `api-contracts.md`.
 * `PlanningStage` is the active stage that drives progress UI.
 */

/** The six in-world planning stages of the adventure. */
export type PlanningStage =
  | "setup"
  | "discover"
  | "logistics"
  | "build"
  | "refine"
  | "wrap";

/** A shared party room the group plans in. */
export interface PartyRoom {
  id: string;
  name: string;
  ownerId: string;
  status: string;
  planningStage: PlanningStage;
}

/** A member (guest) participating in a party room. */
export interface RoomMember {
  id: string;
  roomId: string;
  guestId: string;
  characterId?: string;
  role: string;
}
