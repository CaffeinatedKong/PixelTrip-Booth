/**
 * Mock guest service.
 *
 * In-memory implementation of {@link GuestService} returning contract-shaped
 * fixture data (no Supabase/FastAPI access). `createGuest` generates a
 * client-side UUID and echoes the supplied `displayName`, mirroring the
 * no-auth guest model in `api-contracts.md`.
 */
import type { Guest } from "@/types";
import { mockGuestsById } from "@/mocks";
import type { CreateGuestInput, GuestService } from "./guest.contract";

export class MockGuestService implements GuestService {
  async createGuest(input: CreateGuestInput): Promise<Guest> {
    const guest: Guest = {
      id: crypto.randomUUID(),
      displayName: input.displayName,
      ...(input.avatarUrl !== undefined ? { avatarUrl: input.avatarUrl } : {}),
    };
    return Promise.resolve(guest);
  }

  async getGuest(guestId: string): Promise<Guest | null> {
    return Promise.resolve(mockGuestsById[guestId] ?? null);
  }
}
