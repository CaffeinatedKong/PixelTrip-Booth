/**
 * Guest service contract.
 *
 * Typed method signatures only — no feature or business logic. Behaviour is
 * supplied solely by the mock (`guest.mock.ts`) or real (`guest.api.ts`)
 * implementation. Shapes mirror the "Guest Identity Flow" section of
 * `api-contracts.md` (the single source of truth). No Supabase/FastAPI types
 * appear in this surface.
 */
import type { Guest } from "@/types";

/** Input for {@link GuestService.createGuest}. */
export interface CreateGuestInput {
  displayName: string;
  avatarUrl?: string;
}

export interface GuestService {
  createGuest(input: CreateGuestInput): Promise<Guest>;
  getGuest(guestId: string): Promise<Guest | null>;
}
