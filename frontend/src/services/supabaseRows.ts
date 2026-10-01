/**
 * Row mappers for direct (anon-key) Supabase reads.
 *
 * Supabase returns snake_case database rows; the service layer exposes the
 * camelCase contract shapes from `api-contracts.md`. Only real services
 * (`*.api.ts`) use this module.
 */
import { ApiError } from "@/lib/errors";
import type { Guest, PartyRoom, RoomMember } from "@/types";

/** Columns selected for each table — exactly the contract fields. */
export const ROOM_COLUMNS = "id, room_code, name, status, planning_stage";
export const MEMBER_COLUMNS = "id, room_id, guest_id, display_name, role";
export const GUEST_COLUMNS = "id, display_name, avatar_url";

export interface RoomRow {
  id: string;
  room_code: string;
  name: string;
  status: PartyRoom["status"];
  planning_stage: PartyRoom["planningStage"];
}

export interface MemberRow {
  id: string;
  room_id: string;
  guest_id: string;
  display_name: string;
  role: RoomMember["role"];
}

export interface GuestRow {
  id: string;
  display_name: string;
  avatar_url: string | null;
}

export function toPartyRoom(row: RoomRow): PartyRoom {
  return {
    id: row.id,
    roomCode: row.room_code,
    name: row.name,
    status: row.status,
    planningStage: row.planning_stage,
  };
}

export function toRoomMember(row: MemberRow): RoomMember {
  return {
    id: row.id,
    roomId: row.room_id,
    guestId: row.guest_id,
    displayName: row.display_name,
    role: row.role,
  };
}

export function toGuest(row: GuestRow): Guest {
  return {
    id: row.id,
    displayName: row.display_name,
    avatarUrl: row.avatar_url,
  };
}

/** Convert a Supabase query error into the service layer's {@link ApiError}. */
export function supabaseReadError(table: string): ApiError {
  return new ApiError("DATABASE_ERROR", `Could not read ${table}.`, null);
}
