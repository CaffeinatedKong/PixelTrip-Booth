/**
 * Feature-local type definitions for the Lobby / Character Creation screen.
 *
 * These models are intentionally scoped to the `party-lobby` feature and MUST NOT
 * modify the shared contract types in `src/types`. They stay compatible *in spirit*
 * with the shared `Character` / `TravelPreferences` shapes so a real service could
 * later map between them, and `SessionCharacter` mirrors the backend request payload
 * 1:1 so a future service can pass it straight through.
 *
 * This feature is frontend-only and session-only: nothing defined here is persisted
 * or sent anywhere while the feature remains in-memory.
 */

// ---------------------------------------------------------------------------
// Composable layered avatar
// ---------------------------------------------------------------------------

/** The named slots that make up a composable 8-bit character, back to front. */
export type SpriteLayerSlot = "base" | "archetype" | "outfit" | "accessory";

/** A single stacked visual layer for the composable avatar. */
export interface SpriteLayer {
  slot: SpriteLayerSlot;
  /** Z-order; lower renders behind higher. */
  order: number;
  /** Asset key resolved to a pixel visual by the renderer. */
  assetKey: string;
}

/** A single entry in the data-driven layer map (selection id -> contributed layer). */
export interface LayerMapEntry {
  slot: SpriteLayerSlot;
  order: number;
  assetKey: string;
}

/** Data-driven mapping: for each slot, selection id -> the layer it contributes. */
export type LayerMap = Readonly<
  Record<SpriteLayerSlot, Readonly<Record<string, LayerMapEntry>>>
>;

// ---------------------------------------------------------------------------
// Character draft (in-memory, not-yet-saved selection set)
// ---------------------------------------------------------------------------

/** A selected activity together with its party priority. */
export interface ActivityDraft {
  name: string;
  priority: "must_have" | "optional";
}

/** A single availability range as ISO 8601 date strings. */
export interface DateRange {
  start: string; // ISO 8601 (YYYY-MM-DD)
  end: string; // ISO 8601 (YYYY-MM-DD)
}

/** The in-memory, not-yet-saved selection set driving the left panel. */
export interface CharacterDraft {
  // Appearance selections.
  archetype: string | null;
  outfit: string | null;
  accessory: string | null;
  palette: string | null;
  // Travel preferences.
  travelStyle: string | null;
  destinations: readonly string[];
  interests: readonly string[];
  activities: readonly ActivityDraft[];
  hardConstraints: readonly string[];
  origin: string;
  /** Raw input text; parsed to a number for the model. */
  budgetText: string;
  /** One or more availability ranges; UI starts with a single range. */
  availableDates: readonly DateRange[];
}

// ---------------------------------------------------------------------------
// Session character (saved, session-only; payload-shaped 1:1)
// ---------------------------------------------------------------------------

/** The appearance block of the saved character. */
export interface SessionCharacterAppearance {
  accessory: string;
  outfit: string;
  palette: string;
}

/**
 * The saved, session-only character. Shaped to match the request payload 1:1 so a
 * future service can pass it straight through (still never persisted here).
 */
export interface SessionCharacter {
  availableDates: readonly DateRange[];
  destinations: readonly string[];
  travelStyle: string | null;
  budget: number | null;
  interests: readonly string[];
  activities: readonly ActivityDraft[];
  hardConstraints: readonly string[];
  origin: string;
  character: {
    appearance: SessionCharacterAppearance;
    spriteKey: string;
  };
}

// ---------------------------------------------------------------------------
// Sidebar view models (from feature-local mock + optional RoomSession)
// ---------------------------------------------------------------------------

/** A single party member as shown in the adventure sidebar. */
export interface PartyMemberView {
  id: string;
  displayName: string;
  archetypeLabel: string;
  spriteKey: string;
}

/** The derived budget readout for the budget panel. */
export interface BudgetView {
  limit: number;
  estimated: number;
  remaining: number; // limit - estimated (may be negative)
  isOverBudget: boolean; // estimated > limit
  overageAmount: number; // max(0, estimated - limit)
}

/** The full adventure sidebar view model. */
export interface AdventureView {
  tripName: string;
  dateRangeLabel: string;
  members: readonly PartyMemberView[];
  capacity: number;
  budget: BudgetView;
}
