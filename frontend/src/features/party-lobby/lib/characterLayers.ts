/**
 * Data-driven layer map for the composable 8-bit character.
 *
 * For each sprite layer slot (`base`, `archetype`, `outfit`, `accessory`) this maps a
 * selection id to the single layer it contributes: `{ slot, order, assetKey }`. The slot
 * ids are reused directly from the local option catalogs in `characterOptions.ts` so the
 * creator UI and the renderer stay in sync.
 *
 * Extensibility: adding a new archetype/outfit/accessory asset is a one-line addition here
 * (a new id -> entry). `resolveLayers` and `CharacterPreview` need no changes.
 *
 * `order` keeps the stack back-to-front: base < archetype < outfit < accessory.
 *
 * NOTE: palette is NOT a sprite layer slot (`SpriteLayerSlot` is only
 * base/archetype/outfit/accessory), so the `PALETTE` catalog is intentionally absent here.
 *
 * `assetKey` is a stable `${slot}:${id}` string; the renderer resolves it to a pixel visual.
 */

import type {
  CharacterDraft,
  LayerMap,
  LayerMapEntry,
  SpriteLayer,
  SpriteLayerSlot,
} from "../types";
import { ACCESSORY, APPEARANCE, OUTFIT } from "./characterOptions";

/** Z-order per slot; lower renders behind higher. Base is always behind the rest. */
const SLOT_ORDER: Readonly<Record<SpriteLayerSlot, number>> = {
  base: 0,
  archetype: 1,
  outfit: 2,
  accessory: 3,
};

/** The id of the single, always-present base layer. */
export const BASE_LAYER_ID = "base";

/** Build the id -> entry record for one slot from its option catalog. */
function buildSlotEntries(
  slot: SpriteLayerSlot,
  options: readonly { id: string }[],
): Readonly<Record<string, LayerMapEntry>> {
  const entries: Record<string, LayerMapEntry> = {};
  for (const option of options) {
    entries[option.id] = {
      slot,
      order: SLOT_ORDER[slot],
      assetKey: `${slot}:${option.id}`,
    };
  }
  return entries;
}

/**
 * The data-driven layer map consumed by `resolveLayers`.
 *
 * - `base`: a single always-present entry (slot order 0).
 * - `archetype`: ids from `APPEARANCE` (explorer, ranger, scholar, wanderer).
 * - `outfit`: ids from `OUTFIT` (casual, backpack, premium, all-weather).
 * - `accessory`: ids from `ACCESSORY` (map, camera, compass, lantern).
 */
export const LAYER_MAP: LayerMap = {
  base: {
    [BASE_LAYER_ID]: {
      slot: "base",
      order: SLOT_ORDER.base,
      assetKey: `base:${BASE_LAYER_ID}`,
    },
  },
  archetype: buildSlotEntries("archetype", APPEARANCE),
  outfit: buildSlotEntries("outfit", OUTFIT),
  accessory: buildSlotEntries("accessory", ACCESSORY),
};

/**
 * Resolve a character draft into the ordered stack of sprite layers to render.
 *
 * Always includes the always-present base layer. For each of the `archetype`, `outfit`,
 * and `accessory` slots, if the draft has a selection (non-null) AND that id exists in the
 * map for that slot, the corresponding layer is added. Unknown ids contribute no layer and
 * never throw, so the returned stack is never empty. Palette is not a sprite layer slot and
 * is intentionally ignored.
 *
 * The result is sorted ascending by `order` (base behind archetype behind outfit behind
 * accessory), giving a stable back-to-front render order.
 */
export function resolveLayers(
  draft: CharacterDraft,
  map: LayerMap,
): readonly SpriteLayer[] {
  const layers: SpriteLayer[] = [];

  const base = map.base[BASE_LAYER_ID];
  if (base) {
    layers.push(base);
  }

  const mappedSlots = ["archetype", "outfit", "accessory"] as const satisfies readonly SpriteLayerSlot[];
  for (const slot of mappedSlots) {
    const selectedId = draft[slot];
    if (selectedId === null) {
      continue;
    }
    const entry: LayerMapEntry | undefined = map[slot][selectedId];
    if (entry) {
      layers.push(entry);
    }
  }

  return layers.sort((a, b) => a.order - b.order);
}
