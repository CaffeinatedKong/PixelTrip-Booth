/**
 * Room service — real (backend-backed) implementation.
 *
 * Placeholder for the Foundation phase: every method throws
 * {@link NotImplementedError} and performs no Supabase/FastAPI access. It holds
 * the shape of the real integration without implementing it, so all backend
 * access stays confined to the service layer. Behaviour arrives when the
 * backend endpoints land; until then run with `NEXT_PUBLIC_SERVICE_MODE=mock`.
 */
import type { PartyRoom, RoomMember } from "@/types";
import { notImplemented } from "@/lib/errors";
import type {
  CreateRoomInput,
  JoinRoomInput,
  RoomService,
} from "./room.contract";

class RoomApiService implements RoomService {
  createRoom(_input: CreateRoomInput): Promise<PartyRoom> {
    throw notImplemented("RoomService.createRoom");
  }

  joinRoom(_input: JoinRoomInput): Promise<RoomMember> {
    throw notImplemented("RoomService.joinRoom");
  }

  getRoom(_roomId: string): Promise<PartyRoom | null> {
    throw notImplemented("RoomService.getRoom");
  }

  listMembers(_roomId: string): Promise<RoomMember[]> {
    throw notImplemented("RoomService.listMembers");
  }
}

/** Singleton real Room service placeholder. */
export const roomApiService: RoomService = new RoomApiService();
