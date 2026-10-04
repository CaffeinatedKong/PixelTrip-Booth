/**
 * Pure draft-projection logic for the Lobby / Character Creation screen.
 *
 * This module is frontend-only and session-only: it performs no I/O, no
 * persistence, and no network access. Every function here is a pure,
 * deterministic projection over the in-memory {@link CharacterDraft}.
 *
 * - {@link canSave} decides whether the draft is complete enough to save.
 * - {@link deriveSpriteKey} derives a deterministic sprite key for the avatar.
 * - {@link toSessionCharacter} projects a complete draft into the payload-shaped
 *   {@link SessionCharacter} (the single projection seam `save()` relies on).
 */
import type {
  CharacterDraft,
  SessionCharacter,
  SessionCharacterAppearance,
} from "@/features/party-lobby/types";

/** Sprite variant suffix. A placeholder until per-variant assets exist. */
const SPRITE_VARIANT_SUFFIX = "01";

/** Fallback sprite key used when no archetype is available. */
const FALLBACK_SPRITE_KEY = `traveller-${SPRITE_VARIANT_SUFFIX}`;

/**
 * Whether the draft holds the minimum selections required to save a character.
 *
 * A character is saveable once its appearance core is complete: `archetype`,
 * `outfit`, and `accessory` are all set (non-null). Palette, travel style, and
 * all travel-preference fields are optional and do NOT gate saving.
 *
 * @param draft - The in-memory character draft.
 * @returns `true` iff `archetype`, `outfit`, and `accessory` are all non-null.
 */
export function canSave(draft: CharacterDraft): boolean {
  return (
    draft.archetype !== null &&
    draft.outfit !== null &&
    draft.accessory !== null
  );
}

/**
 * Derive a deterministic sprite key from the archetype and appearance.
 *
 * The canonical key is archetype-based (e.g. `"explorer-01"`). Because
 * {@link SessionCharacterAppearance} carries only `accessory`/`outfit`/`palette`
 * (not the archetype), the archetype is passed explicitly. The result is the
 * lowercased archetype id joined with a sprite-variant suffix; the suffix is a
 * placeholder sprite variant until per-variant assets are introduced. The
 * `appearance` parameter is part of the deterministic key contract and keeps the
 * signature stable for future appearance-driven variants.
 *
 * @param archetype - The selected archetype id (e.g. `"explorer"`).
 * @param appearance - The saved appearance block (reserved for future variants).
 * @returns A deterministic sprite key such as `"explorer-01"`, or
 *   `"traveller-01"` when `archetype` is empty.
 */
export function deriveSpriteKey(
  archetype: string,
  appearance: SessionCharacterAppearance,
): string {
  void appearance;
  const normalized = archetype.trim().toLowerCase();
  if (normalized === "") {
    return FALLBACK_SPRITE_KEY;
  }
  return `${normalized}-${SPRITE_VARIANT_SUFFIX}`;
}

/**
 * Parse raw budget input text into a non-negative number, or `null`.
 *
 * Empty, whitespace-only, non-finite, or negative inputs resolve to `null`
 * rather than throwing, matching the numeric input's `min=0` contract.
 *
 * @param budgetText - The raw budget input text.
 * @returns A finite, non-negative number, or `null`.
 */
function parseBudget(budgetText: string): number | null {
  const trimmed = budgetText.trim();
  if (trimmed === "") {
    return null;
  }
  const value = Number(trimmed);
  if (!Number.isFinite(value) || value < 0) {
    return null;
  }
  return value;
}

/**
 * Project a complete draft into the payload-shaped {@link SessionCharacter}.
 *
 * Returns `null` when the draft is not saveable (see {@link canSave}). Otherwise
 * copies the travel-preference fields verbatim, parses the budget text to a
 * number (or `null`), and builds `character.appearance` plus a derived
 * `spriteKey`. Pure: no I/O, no storage, no fetch.
 *
 * @param draft - The in-memory character draft.
 * @returns The payload-shaped session character, or `null` when not saveable.
 */
export function toSessionCharacter(
  draft: CharacterDraft,
): SessionCharacter | null {
  if (!canSave(draft)) {
    return null;
  }

  // Guaranteed non-null by `canSave`.
  const appearance: SessionCharacterAppearance = {
    accessory: draft.accessory!,
    outfit: draft.outfit!,
    palette: draft.palette ?? "",
  };

  return {
    availableDates: draft.availableDates,
    destinations: draft.destinations,
    travelStyle: draft.travelStyle,
    budget: parseBudget(draft.budgetText),
    interests: draft.interests,
    activities: draft.activities,
    hardConstraints: draft.hardConstraints,
    origin: draft.origin,
    character: {
      appearance,
      spriteKey: deriveSpriteKey(draft.archetype!, appearance),
    },
  };
}
