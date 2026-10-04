/**
 * Frontend-local option catalogs for the 8-bit character creator.
 *
 * UI-only placeholders. These ids/labels and sprite keys are NOT a backend
 * contract — there is no character backend yet. When a real character/preferences
 * service lands, the authoritative option set should come from `api-contracts.md`
 * and these local catalogs can be replaced. Nothing here is sent anywhere.
 */

/** A single selectable option with a stable id and a human-facing label. */
export interface CharacterOption {
  /** Stable id used in local selection state (and, later, by a real service). */
  id: string;
  /** Human-facing label rendered on the option button. */
  label: string;
}

/** Appearance options — the id doubles as the preview sprite key placeholder. */
export const APPEARANCE: readonly CharacterOption[] = [
  { id: "explorer", label: "Explorer" },
  { id: "ranger", label: "Ranger" },
  { id: "scholar", label: "Scholar" },
  { id: "wanderer", label: "Wanderer" },
] as const;

/** Outfit options. */
export const OUTFIT: readonly CharacterOption[] = [
  { id: "casual", label: "Casual" },
  { id: "backpack", label: "Backpack" },
  { id: "premium", label: "Premium" },
  { id: "all-weather", label: "All-weather" },
] as const;

/** Accessory options. */
export const ACCESSORY: readonly CharacterOption[] = [
  { id: "map", label: "Map" },
  { id: "camera", label: "Camera" },
  { id: "compass", label: "Compass" },
  { id: "lantern", label: "Lantern" },
] as const;

/** Travel-style options (single-select). */
export const TRAVEL_STYLE: readonly CharacterOption[] = [
  { id: "backpacker", label: "Backpacker" },
  { id: "luxury", label: "Luxury" },
  { id: "balanced", label: "Balanced" },
  { id: "foodie", label: "Foodie" },
  { id: "adventure", label: "Adventure" },
] as const;

/** Interest options (multi-select). */
export const INTERESTS: readonly CharacterOption[] = [
  { id: "food", label: "Food" },
  { id: "museums", label: "Museums" },
  { id: "nature", label: "Nature" },
  { id: "nightlife", label: "Nightlife" },
  { id: "shopping", label: "Shopping" },
  { id: "history", label: "History" },
] as const;

/** Activity options (multi-select). */
export const ACTIVITIES: readonly CharacterOption[] = [
  { id: "hiking", label: "Hiking" },
  { id: "markets", label: "Markets" },
  { id: "beaches", label: "Beaches" },
  { id: "temples", label: "Temples" },
  { id: "tours", label: "Tours" },
  { id: "relaxing", label: "Relaxing" },
] as const;

/** Placeholder sprite key for the preview before any appearance is chosen. */
export const DEFAULT_SPRITE_KEY = "none";
