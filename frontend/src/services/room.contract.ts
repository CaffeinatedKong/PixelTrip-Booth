/**
 * Room service contract.
 *
 * Typed method signatures only — no feature or business logic. Behaviour is
 * supplied solely by the mock (`room.mock.ts`) or real (`room.api.ts`)
 * implementation. Shapes mirror the room/member contract in
 * `api-contracts.md` (the single source of truth). No Supabase/FastAPI types
 * appear in this surface.
 */
import type { PartyRoom, RoomMember } from "@/types";

/** Input for {@link RoomService.createRoom}. */
export interface CreateRoomInput {
  name: string;
  ownerId: string;
}

/** Input for {@link RoomService.joinRoom}. */
export interface JoinRoomInput {
  roomId: string;
  guestId: string;
  characterId?: string;
}

export interface RoomService {
  createRoom(input: CreateRoomInput): Promise<PartyRoom>;
  joinRoom(input: JoinRoomInput): Promise<RoomMember>;
  getRoom(roomId: string): Promise<PartyRoom | null>;
  listMembers(roomId: string): Promise<RoomMember[]>;
}
