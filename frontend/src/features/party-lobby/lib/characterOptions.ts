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
  /** Optional one-line description shown on richer card groups (e.g. vibes). */
  description?: string;
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
 * Destination VIBES (multi-select). Rather than specific cities, the user picks the
 * kind of trip they feel like — "Where do you feel like going?". These are the
 * free-form destination preferences sent to the planner.
 */
export const DESTINATIONS: readonly CharacterOption[] = [
  { id: "asia", label: "Asia", description: "Rich cultures & buzzing cities" },
  {
    id: "western-cities",
    label: "Western Cities",
    description: "Architecture, culture & nightlife",
  },
  {
    id: "beach-escape",
    label: "Beach Escape",
    description: "Sun, sand & crystal waters",
  },
  {
    id: "nature-scenery",
    label: "Nature & Scenery",
    description: "Mountains, forests & wild beauty",
  },
  {
    id: "food-trip",
    label: "Food Trip",
    description: "Eat your way around the world",
  },
  {
    id: "cultural-trip",
    label: "Cultural Trip",
    description: "History, art & local traditions",
  },
  {
    id: "adventure-trip",
    label: "Adventure Trip",
    description: "Thrills, trails & unforgettable moments",
  },
  {
    id: "shopping-city",
    label: "Shopping City",
    description: "Fashion, markets & retail therapy",
  },
  {
    id: "hidden-gems",
    label: "Hidden Gems",
    description: "Off-the-beaten-path discoveries",
  },
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
