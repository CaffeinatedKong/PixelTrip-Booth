/**
 * Frontend-local option catalogs for the RPG-style character/preference setup.
 *
 * UI-only placeholders. These ids/labels are not a backend contract — when a real
 * preferences service lands, the authoritative sets come from `api-contracts.md`.
 * Nothing here is sent anywhere while the feature is in-memory.
 */

/** A single selectable option with a stable id and a human-facing label. */
export interface CharacterOption {
  /** Stable id used in local selection state (and, later, by a real service). */
  id: string;
  /** Human-facing label rendered on the option card. */
  label: string;
}

/** Step 1 — budget tier (single-select). */
export const BUDGET_TIERS: readonly CharacterOption[] = [
  { id: "low", label: "Low Budget" },
  { id: "medium", label: "Medium Budget" },
  { id: "high", label: "High Budget" },
] as const;

/** Step 2 — group-trip role (single-select); drives the character's identity. */
export const GROUP_ROLES: readonly CharacterOption[] = [
  { id: "leader", label: "Leader" },
  { id: "planner", label: "Planner" },
  { id: "follower", label: "Follower" },
  { id: "chill", label: "Chill" },
  { id: "adventurer", label: "Adventurer" },
] as const;

/** Step 3 — what the user wants most from the trip (multi-select). */
export const TRIP_PRIORITIES: readonly CharacterOption[] = [
  { id: "food", label: "Food" },
  { id: "scenery", label: "Scenery" },
  { id: "adventure", label: "Adventure" },
  { id: "shopping", label: "Shopping" },
  { id: "nightlife", label: "Nightlife" },
  { id: "culture", label: "Culture" },
  { id: "relaxation", label: "Relaxation" },
  { id: "hidden-gems", label: "Hidden Gems" },
  { id: "flexibility", label: "Flexibility" },
] as const;

/**
 * Suggested destination options (multi-select). Destinations remain free-form in
 * the payload; these are UI suggestions, not an exhaustive list.
 */
export const DESTINATIONS: readonly CharacterOption[] = [
  { id: "tokyo", label: "Tokyo" },
  { id: "seoul", label: "Seoul" },
  { id: "bangkok", label: "Bangkok" },
  { id: "paris", label: "Paris" },
] as const;

/** Activity options (multi-select tags). */
export const ACTIVITIES: readonly CharacterOption[] = [
  { id: "hiking", label: "Hiking" },
  { id: "markets", label: "Markets" },
  { id: "beaches", label: "Beaches" },
  { id: "temples", label: "Temples" },
  { id: "tours", label: "Tours" },
  { id: "relaxing", label: "Relaxing" },
] as const;
