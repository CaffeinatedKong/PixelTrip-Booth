/**
 * Guest fixtures.
 *
 * Contract-shaped `Guest` data (see "Guest Identity Flow" in
 * `api-contracts.md`). Consumed only by the mock service implementations,
 * never imported by the UI. IDs are UUID-format strings.
 */
import type { Guest } from "@/types";

/** A stable fixture guest returned by `guest.mock.ts` lookups. */
export const mockGuest: Guest = {
  id: "11111111-1111-4111-8111-111111111111",
  displayName: "Pixel Wanderer",
  avatarUrl: "sprite:explorer-01",
};

/** Keyed guests for id lookups; unknown ids resolve to `null`. */
export const mockGuestsById: Readonly<Record<string, Guest>> = {
  [mockGuest.id]: mockGuest,
};
