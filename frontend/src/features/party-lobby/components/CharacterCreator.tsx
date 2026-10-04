"use client";

/**
 * CharacterCreator — a local-only 8-bit character + travel-preferences creator.
 *
 * UI ONLY. There is no character/preferences backend yet, so every selection
 * lives in this component's local state and NOTHING is persisted or synced:
 * "Save character (local)" just stores the current selection in local state and
 * shows an honest confirmation line. No service import, no Supabase, no fetch.
 *
 * Structured so a real service can be dropped in later: the saved selection is a
 * single typed object ({@link CharacterDraft}) and the Save handler is the one
 * seam a `characterService.save(draft)` call would replace.
 *
 * Presentational + local state only. Click-through option groups use
 * {@link PixelButton} with `aria-pressed`; the {@link CharacterSprite} preview's
 * sprite key reflects the selected appearance id.
 */
import { useId, useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import { PixelCard } from "@/components/PixelCard";
import { CharacterSprite } from "@/components/CharacterSprite";

import {
  ACCESSORY,
  ACTIVITIES,
  APPEARANCE,
  DEFAULT_SPRITE_KEY,
  INTERESTS,
  OUTFIT,
  TRAVEL_STYLE,
  type CharacterOption,
} from "../lib/characterOptions";

/** The complete local selection, shaped for a future service to consume. */
export interface CharacterDraft {
  appearance: string | null;
  outfit: string | null;
  accessory: string | null;
  travelStyle: string | null;
  interests: string[];
  activities: string[];
  budget: number | null;
  availabilityStart: string;
  availabilityEnd: string;
}

export interface CharacterCreatorProps {
  /** The viewer's display name, used to personalise the preview label. */
  viewerDisplayName: string;
}

/** A single-select row of option buttons. */
function OptionGroup({
  legend,
  options,
  selected,
  onSelect,
}: {
  legend: string;
  options: readonly CharacterOption[];
  selected: string | null;
  onSelect: (id: string) => void;
}): ReactElement {
  return (
    <fieldset className="flex flex-col gap-8">
      <legend className="font-display text-ink mb-8">{legend}</legend>
      <div className="flex flex-wrap gap-8">
        {options.map((option) => (
          <PixelButton
            key={option.id}
            variant="option"
            label={option.label}
            ariaPressed={selected === option.id}
            onClick={() => onSelect(option.id)}
          />
        ))}
      </div>
    </fieldset>
  );
}

/** A multi-select row of toggle option buttons. */
function MultiOptionGroup({
  legend,
  options,
  selected,
  onToggle,
}: {
  legend: string;
  options: readonly CharacterOption[];
  selected: string[];
  onToggle: (id: string) => void;
}): ReactElement {
  return (
    <fieldset className="flex flex-col gap-8">
      <legend className="font-display text-ink mb-8">{legend}</legend>
      <div className="flex flex-wrap gap-8">
        {options.map((option) => (
          <PixelButton
            key={option.id}
            variant="option"
            label={option.label}
            ariaPressed={selected.includes(option.id)}
            onClick={() => onToggle(option.id)}
          />
        ))}
      </div>
    </fieldset>
  );
}

export function CharacterCreator({
  viewerDisplayName,
}: CharacterCreatorProps): ReactElement {
  const budgetId = useId();
  const startId = useId();
  const endId = useId();

  const [appearance, setAppearance] = useState<string | null>(null);
  const [outfit, setOutfit] = useState<string | null>(null);
  const [accessory, setAccessory] = useState<string | null>(null);
  const [travelStyle, setTravelStyle] = useState<string | null>(null);
  const [interests, setInterests] = useState<string[]>([]);
  const [activities, setActivities] = useState<string[]>([]);
  const [budget, setBudget] = useState<string>("");
  const [availabilityStart, setAvailabilityStart] = useState<string>("");
  const [availabilityEnd, setAvailabilityEnd] = useState<string>("");
  const [savedDraft, setSavedDraft] = useState<CharacterDraft | null>(null);

  const toggle =
    (setter: (updater: (prev: string[]) => string[]) => void) =>
    (id: string): void => {
      setter((prev) =>
        prev.includes(id)
          ? prev.filter((value) => value !== id)
          : [...prev, id],
      );
    };

  // Save is allowed once the three appearance fields are chosen.
  const canSave =
    appearance !== null && outfit !== null && accessory !== null;

  const spriteKey = appearance ?? DEFAULT_SPRITE_KEY;

  // The single persistence seam. A real service would replace this body with a
  // `characterService.save(draft)` call; the UI above it does not change.
  const save = (): void => {
    if (!canSave) return;
    const parsedBudget = budget.trim() === "" ? null : Number(budget);
    setSavedDraft({
      appearance,
      outfit,
      accessory,
      travelStyle,
      interests,
      activities,
      budget:
        parsedBudget !== null && Number.isFinite(parsedBudget)
          ? parsedBudget
          : null,
      availabilityStart,
      availabilityEnd,
    });
  };

  return (
    <PixelCard title="Create your character">
      <p className="font-body text-muted mb-16">
        Saved on your screen only — not yet sent to the party/backend.
      </p>

      <div className="flex items-center gap-16 mb-16">
        <CharacterSprite
          spriteKey={spriteKey}
          label={`${viewerDisplayName}'s character preview`}
          size="lg"
        />
        <p className="font-body">
          {appearance === null
            ? "Pick an appearance to preview your character."
            : "Your character takes shape…"}
        </p>
      </div>

      <div className="flex flex-col gap-24">
        <OptionGroup
          legend="Appearance"
          options={APPEARANCE}
          selected={appearance}
          onSelect={setAppearance}
        />
        <OptionGroup
          legend="Outfit"
          options={OUTFIT}
          selected={outfit}
          onSelect={setOutfit}
        />
        <OptionGroup
          legend="Accessory"
          options={ACCESSORY}
          selected={accessory}
          onSelect={setAccessory}
        />
        <OptionGroup
          legend="Travel style"
          options={TRAVEL_STYLE}
          selected={travelStyle}
          onSelect={setTravelStyle}
        />
        <MultiOptionGroup
          legend="Interests"
          options={INTERESTS}
          selected={interests}
          onToggle={toggle(setInterests)}
        />
        <MultiOptionGroup
          legend="Activities"
          options={ACTIVITIES}
          selected={activities}
          onToggle={toggle(setActivities)}
        />

        <div className="flex flex-col gap-8">
          <label htmlFor={budgetId} className="font-display text-ink">
            Budget
          </label>
          <input
            id={budgetId}
            type="number"
            min={0}
            value={budget}
            onChange={(event) => setBudget(event.target.value)}
            placeholder="e.g. 1500"
            className="font-body text-ink bg-bg border-2 border-muted px-16 py-8"
          />
        </div>

        <div className="flex flex-col gap-8">
          <label htmlFor={startId} className="font-display text-ink">
            Available from
          </label>
          <input
            id={startId}
            type="date"
            value={availabilityStart}
            onChange={(event) => setAvailabilityStart(event.target.value)}
            className="font-body text-ink bg-bg border-2 border-muted px-16 py-8"
          />
        </div>

        <div className="flex flex-col gap-8">
          <label htmlFor={endId} className="font-display text-ink">
            Available until
          </label>
          <input
            id={endId}
            type="date"
            value={availabilityEnd}
            onChange={(event) => setAvailabilityEnd(event.target.value)}
            className="font-body text-ink bg-bg border-2 border-muted px-16 py-8"
          />
        </div>
      </div>

      <div className="flex flex-col gap-8 mt-24">
        <PixelButton
          variant="primary"
          label="Save character (local)"
          ariaLabel="Save character locally"
          disabled={!canSave}
          onClick={save}
        />
        {!canSave ? (
          <p className="font-body text-muted">
            Choose an appearance, outfit, and accessory to save your character.
          </p>
        ) : null}
        <p role="status" aria-live="polite" className="font-body min-h-8">
          {savedDraft
            ? "Character saved on your screen only — not yet sent to the party/backend."
            : ""}
        </p>
      </div>
    </PixelCard>
  );
}

export default CharacterCreator;
