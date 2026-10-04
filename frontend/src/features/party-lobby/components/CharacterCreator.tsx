"use client";

/**
 * CharacterCreator — the left-panel host of the 8-bit character creator.
 *
 * Owns {@link useCharacterDraft} (the feature's single stateful hook) and composes
 * the already-built feature components into one screen: a layered
 * {@link CharacterPreview}, five single-select {@link OptionCardGroup}s (Archetype,
 * Outfit, Accessory, Palette, Travel Style), two multi-select
 * {@link OptionTagGroup}s (Interests, Destinations), an {@link ActivityPriorityGroup}
 * for Activities, a {@link PreferenceFields} block, and the primary "SAVE CHARACTER"
 * {@link PixelButton}.
 *
 * Presentational composition only: this component reimplements none of the group
 * UI and performs no data fetching, persistence, or service calls. All draft state
 * and the single `save()` projection seam live in the hook. While the save is
 * gated (`!canSave`) a visible explanatory line lists the still-required
 * appearance selections; after a successful save a polite `role="status"` live
 * region announces that the character is kept for this session only and is not
 * persisted to any server.
 *
 * Styling uses design-token utility classes only — never raw hex or arbitrary
 * magic values.
 */
import { type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";

import { ActivityPriorityGroup } from "./ActivityPriorityGroup";
import { CharacterPreview } from "./CharacterPreview";
import { OptionCardGroup } from "./OptionCardGroup";
import { OptionTagGroup } from "./OptionTagGroup";
import { PreferenceFields } from "./PreferenceFields";
import { useCharacterDraft } from "../hooks/useCharacterDraft";
import { LAYER_MAP, resolveLayers } from "../lib/characterLayers";
import {
  ACCESSORY,
  ACTIVITIES,
  APPEARANCE,
  DESTINATIONS,
  INTERESTS,
  OUTFIT,
  PALETTE,
  TRAVEL_STYLE,
} from "../lib/characterOptions";

export interface CharacterCreatorProps {
  /** The viewer's display name, used to personalise the preview label. */
  viewerDisplayName: string;
}

export function CharacterCreator({
  viewerDisplayName,
}: CharacterCreatorProps): ReactElement {
  const {
    draft,
    select,
    toggle,
    toggleActivity,
    setActivityPriority,
    setBudgetText,
    setOrigin,
    addConstraint,
    removeConstraint,
    setDateRange,
    addDateRange,
    removeDateRange,
    canSave,
    sessionCharacter,
    save,
  } = useCharacterDraft();

  const layers = resolveLayers(draft, LAYER_MAP);

  // The appearance core that gates saving (see `canSave` in ../lib/draft).
  const missingSelections: readonly string[] = [
    draft.archetype === null ? "archetype" : null,
    draft.outfit === null ? "outfit" : null,
    draft.accessory === null ? "accessory" : null,
  ].filter((label): label is string => label !== null);

  // Polite live-region copy. Empty before any successful save so assistive tech
  // only announces once a session character exists.
  const saveStatusMessage =
    sessionCharacter !== null
      ? "Character saved for this session only — not saved to any server."
      : "";

  return (
    <section className="flex flex-col gap-24">
      <header className="flex flex-col gap-8">
        <h2 className="font-display text-ink">CREATE YOUR CHARACTER</h2>
        <p className="font-body text-muted">
          Build your traveller for the adventure.
        </p>
      </header>

      <CharacterPreview
        layers={layers}
        palette={draft.palette}
        travelStyle={draft.travelStyle}
        label={`${viewerDisplayName}'s character`}
      />

      <OptionCardGroup
        legend="Archetype"
        options={APPEARANCE}
        selectedId={draft.archetype}
        onSelect={(id) => select("archetype", id)}
      />
      <OptionCardGroup
        legend="Outfit"
        options={OUTFIT}
        selectedId={draft.outfit}
        onSelect={(id) => select("outfit", id)}
      />
      <OptionCardGroup
        legend="Accessory"
        options={ACCESSORY}
        selectedId={draft.accessory}
        onSelect={(id) => select("accessory", id)}
      />
      <OptionCardGroup
        legend="Palette"
        options={PALETTE}
        selectedId={draft.palette}
        onSelect={(id) => select("palette", id)}
      />
      <OptionCardGroup
        legend="Travel Style"
        options={TRAVEL_STYLE}
        selectedId={draft.travelStyle}
        onSelect={(id) => select("travelStyle", id)}
      />

      <OptionTagGroup
        legend="Interests"
        options={INTERESTS}
        selectedIds={draft.interests}
        onToggle={(id) => toggle("interests", id)}
      />
      <OptionTagGroup
        legend="Destinations"
        options={DESTINATIONS}
        selectedIds={draft.destinations}
        onToggle={(id) => toggle("destinations", id)}
      />

      <ActivityPriorityGroup
        legend="Activities"
        options={ACTIVITIES}
        selected={draft.activities}
        onToggle={(name) => toggleActivity(name)}
        onPriorityChange={(name, priority) =>
          setActivityPriority(name, priority)
        }
      />

      <PreferenceFields
        budgetText={draft.budgetText}
        onBudgetChange={setBudgetText}
        origin={draft.origin}
        onOriginChange={setOrigin}
        hardConstraints={draft.hardConstraints}
        onAddConstraint={addConstraint}
        onRemoveConstraint={removeConstraint}
        availableDates={draft.availableDates}
        onDateRangeChange={setDateRange}
        onAddDateRange={addDateRange}
        onRemoveDateRange={removeDateRange}
      />

      <div className="flex flex-col gap-8">
        {!canSave ? (
          <p className="font-body text-muted">
            {missingSelections.length > 0
              ? `Still required to save: ${missingSelections.join(", ")}.`
              : "Choose an archetype, outfit, and accessory to save."}
          </p>
        ) : null}

        <PixelButton
          variant="primary"
          type="button"
          label="SAVE CHARACTER"
          disabled={!canSave}
          onClick={save}
        />

        {/* Polite live region: always present so assistive tech picks up the
            change; empty until a save produces a session character. */}
        <p role="status" aria-live="polite" className="font-body text-muted">
          {saveStatusMessage}
        </p>
      </div>
    </section>
  );
}

export default CharacterCreator;
