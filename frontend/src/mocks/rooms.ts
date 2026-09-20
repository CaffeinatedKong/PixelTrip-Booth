/**
 * Party room and membership fixtures.
 *
 * Contract-shaped `PartyRoom` / `RoomMember` data (see the room/member and
 * "Stage & State" sections of `api-contracts.md`). Consumed only by the mock
 * service implementations. IDs are UUID-format strings.
 */
import type { PartyRoom, RoomMember } from "@/types";

/** A stable fixture room returned by `room.mock.ts` lookups. */
export const mockRoom: PartyRoom = {
  id: "22222222-2222-4222-8222-222222222222",
  name: "The Wandering Party",
  ownerId: "11111111-1111-4111-8111-111111111111",
  status: "active",
  planningStage: "setup",
};

/** Fixture members belonging to {@link mockRoom}. */
export const mockRoomMembers: readonly RoomMember[] = [
  {
    id: "33333333-3333-4333-8333-333333333333",
    roomId: mockRoom.id,
    guestId: "11111111-1111-4111-8111-111111111111",
    characterId: "44444444-4444-4444-8444-444444444444",
    role: "owner",
  },
  {
    id: "55555555-5555-4555-8555-555555555555",
    roomId: mockRoom.id,
    guestId: "66666666-6666-4666-8666-666666666666",
    role: "member",
  },
];

/** Keyed rooms for id lookups; unknown ids resolve to `null`. */
export const mockRoomsById: Readonly<Record<string, PartyRoom>> = {
  [mockRoom.id]: mockRoom,
};
