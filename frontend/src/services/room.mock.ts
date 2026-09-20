/**
 * Mock room service.
 *
 * In-memory implementation of {@link RoomService} returning contract-shaped
 * fixture data (no Supabase/FastAPI access). `createRoom`/`joinRoom` generate
 * client-side UUIDs and echo the supplied input; lookups resolve from
 * fixtures or `null`.
 */
import type { PartyRoom, RoomMember } from "@/types";
import { mockRoomMembers, mockRoomsById } from "@/mocks";
import type {
  CreateRoomInput,
  JoinRoomInput,
  RoomService,
} from "./room.contract";

export class MockRoomService implements RoomService {
  async createRoom(input: CreateRoomInput): Promise<PartyRoom> {
    const room: PartyRoom = {
      id: crypto.randomUUID(),
      name: input.name,
      ownerId: input.ownerId,
      status: "active",
      planningStage: "setup",
    };
    return Promise.resolve(room);
  }

  async joinRoom(input: JoinRoomInput): Promise<RoomMember> {
    const member: RoomMember = {
      id: crypto.randomUUID(),
      roomId: input.roomId,
      guestId: input.guestId,
      ...(input.characterId !== undefined
        ? { characterId: input.characterId }
        : {}),
      role: "member",
    };
    return Promise.resolve(member);
  }

  async getRoom(roomId: string): Promise<PartyRoom | null> {
    return Promise.resolve(mockRoomsById[roomId] ?? null);
  }

  async listMembers(roomId: string): Promise<RoomMember[]> {
    return Promise.resolve(
      mockRoomMembers.filter((member) => member.roomId === roomId),
    );
  }
}
