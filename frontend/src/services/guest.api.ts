/**
 * Guest service — real (backend-backed) implementation.
 *
 * Placeholder for the Foundation phase: every method throws
 * {@link NotImplementedError} and performs no Supabase/FastAPI access. It holds
 * the shape of the real integration without implementing it, so all backend
 * access stays confined to the service layer. Behaviour arrives when the
 * backend endpoints land; until then run with `NEXT_PUBLIC_SERVICE_MODE=mock`.
 */
import type { Guest } from "@/types";
import { notImplemented } from "@/lib/errors";
import type { CreateGuestInput, GuestService } from "./guest.contract";

class GuestApiService implements GuestService {
  createGuest(_input: CreateGuestInput): Promise<Guest> {
    throw notImplemented("GuestService.createGuest");
  }

  getGuest(_guestId: string): Promise<Guest | null> {
    throw notImplemented("GuestService.getGuest");
  }
}

/** Singleton real Guest service placeholder. */
export const guestApiService: GuestService = new GuestApiService();
