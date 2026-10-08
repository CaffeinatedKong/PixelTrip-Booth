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
  /** Optional emoji/icon shown on card groups. */
  icon?: string;
}

/** Step 1 — budget tier (single-select). */
export const BUDGET_TIERS: readonly CharacterOption[] = [
  { id: "low", label: "Low Budget", icon: "🪙", description: "Hostels & street eats" },
  {
    id: "medium",
    label: "Medium Budget",
    icon: "💰",
    description: "Comfy stays & nice meals",
  },
  {
    id: "high",
    label: "High Budget",
    icon: "💎",
    description: "Premium stays & fine dining",
  },
] as const;

/** Step 2 — group-trip role (single-select); drives the character's identity. */
export const GROUP_ROLES: readonly CharacterOption[] = [
  { id: "leader", label: "Leader", icon: "👑", description: "Rallies the party & decides" },
  {
    id: "planner",
    label: "Planner",
    icon: "📋",
    description: "Maps out every detail",
  },
  {
    id: "follower",
    label: "Follower",
    icon: "🧭",
    description: "Happy to go with the flow",
  },
  { id: "chill", label: "Chill", icon: "😎", description: "Relaxed, no stress" },
  {
    id: "adventurer",
    label: "Adventurer",
    icon: "🎒",
    description: "Chases the next thrill",
  },
] as const;

/** Step 3 — what the user wants most from the trip (multi-select). */
export const TRIP_PRIORITIES: readonly CharacterOption[] = [
  { id: "food", label: "Food", icon: "🍜", description: "Eat your way around" },
  { id: "scenery", label: "Scenery", icon: "🏞️", description: "Views worth the trip" },
  { id: "adventure", label: "Adventure", icon: "🧗", description: "Thrills & action" },
  { id: "shopping", label: "Shopping", icon: "🛍️", description: "Markets & retail" },
  { id: "nightlife", label: "Nightlife", icon: "🌃", description: "After-dark fun" },
  { id: "culture", label: "Culture", icon: "🏛️", description: "History & art" },
  {
    id: "relaxation",
    label: "Relaxation",
    icon: "🧖",
    description: "Rest & recharge",
  },
  {
    id: "hidden-gems",
    label: "Hidden Gems",
    icon: "💎",
    description: "Off-the-beaten path",
  },
  {
    id: "flexibility",
    label: "Flexibility",
    icon: "🔀",
    description: "Keep plans open",
  },
] as const;

/**
 * Destination VIBES (multi-select). Rather than specific cities, the user picks the
 * kind of trip they feel like — "Where do you feel like going?". These are the
 * free-form destination preferences sent to the planner.
 */
export const DESTINATIONS: readonly CharacterOption[] = [
  { id: "asia", label: "Asia", icon: "🏯", description: "Rich cultures & buzzing cities" },
  {
    id: "western-cities",
    label: "Western Cities",
    icon: "🏙️",
    description: "Architecture, culture & nightlife",
  },
  {
    id: "beach-escape",
    label: "Beach Escape",
    icon: "🏖️",
    description: "Sun, sand & crystal waters",
  },
  {
    id: "nature-scenery",
    label: "Nature & Scenery",
    icon: "🏞️",
    description: "Mountains, forests & wild beauty",
  },
  {
    id: "food-trip",
    label: "Food Trip",
    icon: "🍜",
    description: "Eat your way around the world",
  },
  {
    id: "cultural-trip",
    label: "Cultural Trip",
    icon: "🏛️",
    description: "History, art & local traditions",
  },
  {
    id: "adventure-trip",
    label: "Adventure Trip",
    icon: "🧗",
    description: "Thrills, trails & unforgettable moments",
  },
  {
    id: "shopping-city",
    label: "Shopping City",
    icon: "🛍️",
    description: "Fashion, markets & retail therapy",
  },
  {
    id: "hidden-gems",
    label: "Hidden Gems",
    icon: "💎",
    description: "Off-the-beaten-path discoveries",
  },
] as const;

/** Activity options (multi-select tags). */
export const ACTIVITIES: readonly CharacterOption[] = [
  { id: "hiking", label: "Hiking", icon: "🥾", description: "Trails & peaks" },
  { id: "markets", label: "Markets", icon: "🏮", description: "Local stalls & finds" },
  { id: "beaches", label: "Beaches", icon: "🏖️", description: "Sun & sea" },
  { id: "temples", label: "Temples", icon: "⛩️", description: "Shrines & heritage" },
  { id: "tours", label: "Tours", icon: "🗺️", description: "Guided discovery" },
  { id: "relaxing", label: "Relaxing", icon: "🍹", description: "Slow & easy days" },
] as const;
