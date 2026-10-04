/**
 * Room service — real (backend-backed) implementation.
 *
 * - `createRoom` / `joinRoom` are mutations, so they go through FastAPI
 *   (`POST /rooms`, `POST /rooms/{roomCode}/join`; see "HTTP API" in
 *   `api-contracts.md`).
 * - `getRoom` / `listMembers` are approved direct anon-key Supabase reads (see
 *   `docs/SUPABASE_ACCESS_BOUNDARY.md`).
 *
 * Failures surface as `ApiError`.
 */
import { getApiClient } from "@/lib/apiClient";
import { getSupabaseClient } from "@/lib/supabaseClient";
import type { PartyRoom, RoomMember, RoomSession } from "@/types";

import type {
  CreateRoomInput,
  JoinRoomInput,
  RoomService,
} from "./room.contract";
import {
  MEMBER_COLUMNS,
  type MemberRow,
  ROOM_COLUMNS,
  type RoomRow,
  supabaseReadError,
  toPartyRoom,
  toRoomMember,
} from "./supabaseRows";

class RoomApiService implements RoomService {
  createRoom(input: CreateRoomInput): Promise<RoomSession> {
    return getApiClient().post<RoomSession>("/rooms", {
      name: input.name,
      ownerDisplayName: input.ownerDisplayName,
    });
  }

  joinRoom(input: JoinRoomInput): Promise<RoomSession> {
    // The backend only accepts uppercase codes, so normalise user input first.
    const roomCode = input.roomCode.trim().toUpperCase();
    return getApiClient().post<RoomSession>(
      `/rooms/${encodeURIComponent(roomCode)}/join`,
      { displayName: input.displayName },
    );
  }

  // Direct Supabase access (approved: read-only).
  // Table: party_rooms — room header for a room the user is already in; no side effects.
  // Shape: { id, room_code, name, status, planning_stage } → PartyRoom.
  async getRoom(roomId: string): Promise<PartyRoom | null> {
    const { data, error } = await getSupabaseClient()
      .from("party_rooms")
      .select(ROOM_COLUMNS)
      .eq("id", roomId)
      .maybeSingle<RoomRow>();
    if (error) {
      throw supabaseReadError("party_rooms");
    }
    return data ? toPartyRoom(data) : null;
  }

  // Direct Supabase access (approved: read-only).
  // Table: room_members — the party roster for the current room; no side effects.
  // Shape: { id, room_id, guest_id, display_name, role } → RoomMember[] (join order).
  async listMembers(roomId: string): Promise<RoomMember[]> {
    const { data, error } = await getSupabaseClient()
      .from("room_members")
      .select(MEMBER_COLUMNS)
      .eq("room_id", roomId)
      .order("created_at", { ascending: true })
      .returns<MemberRow[]>();
    if (error) {
      throw supabaseReadError("room_members");
    }
    return (data ?? []).map(toRoomMember);
  }
}

/** Singleton real Room service. */
export const roomApiService: RoomService = new RoomApiService();
