/**
 * Itinerary and versioning shapes.
 *
 * Mirrors the "Itinerary Format" and "Itinerary Versioning" contracts in
 * `api-contracts.md`. The journal, quest log, timeline, and map are all
 * derived from a single `Itinerary` object.
 */

/** A single ordered activity within a day plan. */
export interface ItineraryItem {
  time?: string;
  title: string;
  description?: string;
  location?: string;
  tags?: string[];
}

/** A day plan of ordered activities. */
export interface ItineraryDay {
  day: number;
  date?: string;
  items: ItineraryItem[];
}

/** The full trip plan object. */
export interface Itinerary {
  tripId: string;
  roomId: string;
  title: string;
  summary: string;
  destination: { name: string; country?: string };
  dates?: { start: string; end: string };
  days: ItineraryDay[];
  map?: { label: string; lat: number; lng: number }[];
}

/** A versioned wrapper around an itinerary. Only one is current. */
export interface ItineraryVersion {
  version: number;
  source: "build" | "refine";
  isCurrent: boolean;
  itinerary: Itinerary;
  changeSummary?: string;
}
