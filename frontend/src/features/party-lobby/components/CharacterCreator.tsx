"use client";

/**
 * CharacterCreator — the RPG-style character/preference questionnaire (left panel).
 *
 * The user builds a travel PERSONALITY rather than a detailed avatar. A polished
 * 8-bit chibi sits at the top and reflects the chosen group-trip role; everything
 * below is a concise, pixel-styled questionnaire whose answers are stored as
 * structured trip-planning data (not encoded on the sprite).
 *
 * Steps: budget tier -> group role -> trip priorities -> destinations ->
 * activities -> adventure funds -> availability -> save. Origin is
 * always Singapore and is never requested. Owns {@link useCharacterDraft} for the
 * in-memory draft, and on save submits the preferences + character to the backend
 * via the preferences service (PUT .../preferences) through `getServices()`.
 */
import { useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import { PixelCard } from "@/components/PixelCard";
import { getServices } from "@/services";
import { ApiError } from "@/lib/errors";
import type { RoomSession } from "@/types";

import { CharacterPreview } from "./CharacterPreview";
import { VibeCardGroup } from "./VibeCardGroup";
import { useCharacterDraft } from "../hooks/useCharacterDraft";
import { LAYER_MAP, resolveLayers } from "../lib/characterLayers";
import {
  ACTIVITIES,
  BUDGET_TIERS,
  DESTINATIONS,
  GROUP_ROLES,
  TRIP_PRIORITIES,
} from "../lib/characterOptions";
import {
  FIXED_ORIGIN,
  type BudgetTier,
  type DateRange,
  type GroupRole,
} from "../types";
import { toSessionCharacter } from "../lib/draft";

export interface CharacterCreatorProps {
  /** The active room session (supplies the room code + member id for saving). */
  session: RoomSession;
  /** Called after the character is successfully saved to the backend. */
  onSaved?: () => void;
}

const INPUT_CLASSES =
  "font-body text-ink bg-bg border-2 border-muted px-16 py-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

/** Emoji shown under the character for each selected trip priority. */
const PRIORITY_EMOJI: Readonly<Record<string, string>> = {
  food: "🍜",
  scenery: "🏞️",
  adventure: "🧗",
  shopping: "🛍️",
  nightlife: "🌃",
  culture: "🏛️",
  relaxation: "🧖",
  "hidden-gems": "💎",
  flexibility: "🔀",
};

export function CharacterCreator({
  session,
  onSaved,
}: CharacterCreatorProps): ReactElement {
  const viewerDisplayName = session.member.displayName;
  const {
    draft,
    setBudgetTier,
    setGroupRole,
    toggle,
    setBudgetText,
    setDateRange,
    addDateRange,
    removeDateRange,
    canSave,
    sessionCharacter,
    save,
  } = useCharacterDraft();

  // Submission state for the backend save (explicit loading + error handling).
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [budgetError, setBudgetError] = useState<string | null>(null);
  const [savedOnce, setSavedOnce] = useState(false);

  const handleSave = async (): Promise<void> => {
    if (!canSave || submitting) {
      return;
    }
    // Keep the in-memory session character in sync for the preview/sidebar.
    save();

    const character = toSessionCharacter(draft);
    if (character === null) {
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    try {
      await getServices().preferences.savePreferences({
        roomCode: session.room.roomCode,
        memberId: session.member.id,
        // Payload-shaped preferences. The group-trip role is carried in
        // `travelStyle` (what role you play in the group); tripPriorities map onto
        // the contract's `interests`; activities are sent as plain name tags;
        // origin is always Singapore and is never asked of the user.
        availableDates: character.availableDates,
        destinations: character.destinations,
        travelStyle: character.groupRole,
        budget: character.budget,
        interests: character.tripPriorities,
        activities: character.activities,
        hardConstraints: [],
        origin: FIXED_ORIGIN,
        character: {
          appearance: {
            role: character.groupRole,
            budgetTier: character.budgetTier,
            tripPriorities: character.tripPriorities,
          },
          spriteKey: character.character.spriteKey,
        },
      });
      setSavedOnce(true);
      onSaved?.();
    } catch (error) {
      if (error instanceof ApiError && error.code === "INVALID_BUDGET") {
        // Shown under the funds field, where the member can fix it.
        setBudgetError(error.message);
        return;
      }
      const message =
        error instanceof ApiError
          ? error.message
          : "Could not save your traveller. Please try again.";
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const layers = resolveLayers(draft, LAYER_MAP);
  const canRemoveRange = draft.availableDates.length > 1;

  return (
    <section className="flex flex-col gap-24">
      <header className="flex flex-col gap-8">
        <h2 className="font-display text-ink">CREATE YOUR TRAVELLER</h2>
        <p className="font-body text-muted">
          Answer a few quests to shape your travel personality.
        </p>
      </header>

      {/* 1. Character preview — reflects the chosen group role, with a row of
          trip-priority emoji beneath it. */}
      <PixelCard title="Your traveller">
        <div className="flex flex-col items-center gap-16">
          <CharacterPreview
            layers={layers}
            label={`${viewerDisplayName}'s traveller`}
          />

          {/* Trip-priority emoji badges under the character. */}
          <div
            className="flex min-h-8 flex-wrap items-center justify-center gap-8"
            aria-label="Selected trip priorities"
          >
            {draft.tripPriorities.length > 0 ? (
              draft.tripPriorities.map((id) => (
                <span key={id} title={id} className="text-xl leading-none">
                  {PRIORITY_EMOJI[id] ?? "⭐"}
                </span>
              ))
            ) : (
              <span className="font-body text-muted">
                Pick trip priorities to show what you are after.
              </span>
            )}
          </div>

          <p className="font-body text-muted">
            {draft.groupRole === null
              ? "Choose your group role to bring your traveller to life."
              : "This is you in the party."}
          </p>
        </div>
      </PixelCard>

      {/* 2. Budget tier (single-select). */}
      <VibeCardGroup
        legend="Choose your budget"
        mode="single"
        options={BUDGET_TIERS}
        selectedIds={draft.budgetTier ? [draft.budgetTier] : []}
        onToggle={(id) => setBudgetTier(id as BudgetTier)}
      />

      {/* 3. Group role (single-select) — drives the character. */}
      <VibeCardGroup
        legend="What role do you play in a group trip?"
        mode="single"
        options={GROUP_ROLES}
        selectedIds={draft.groupRole ? [draft.groupRole] : []}
        onToggle={(id) => setGroupRole(id as GroupRole)}
      />

      {/* 4. Trip priorities (multi-select). */}
      <VibeCardGroup
        legend="What do you want most from this trip?"
        options={TRIP_PRIORITIES}
        selectedIds={draft.tripPriorities}
        onToggle={(id) => toggle("tripPriorities", id)}
      />

      {/* 5. Destination vibes (multi-select). */}
      <VibeCardGroup
        legend="Where do you feel like going?"
        options={DESTINATIONS}
        selectedIds={draft.destinations}
        onToggle={(id) => toggle("destinations", id)}
      />

      {/* 7. Activities (multi-select). */}
      <VibeCardGroup
        legend="Activities"
        options={ACTIVITIES}
        selectedIds={draft.activities}
        onToggle={(id) => toggle("activities", id)}
      />

      {/* 8. Adventure funds (numeric). */}
      <div className="flex flex-col gap-8">
        <label htmlFor="pref-budget" className="font-display text-ink">
          ADVENTURE FUNDS
        </label>
        <p id="pref-budget-hint" className="font-body text-muted">
          SGD per person for the whole trip, including flights (100–50,000).
          Leave empty if you are not sure.
        </p>
        <input
          id="pref-budget"
          type="number"
          min={100}
          max={50000}
          value={draft.budgetText}
          onChange={(event) => {
            setBudgetError(null);
            setBudgetText(event.target.value);
          }}
          placeholder="1500"
          aria-describedby="pref-budget-hint"
          aria-invalid={budgetError !== null}
          className={INPUT_CLASSES}
        />
        {budgetError !== null ? (
          <p role="alert" className="font-body text-danger">
            {budgetError}
          </p>
        ) : null}
      </div>

      {/* 9. Availability dates. */}
      <fieldset className="flex flex-col gap-16">
        <legend className="font-display text-ink mb-8">AVAILABLE DATES</legend>
        {draft.availableDates.map((range: DateRange, index: number) => {
          const fromId = `avail-from-${index}`;
          const untilId = `avail-until-${index}`;
          return (
            <div
              key={index}
              className="flex flex-col gap-8 border-2 border-muted px-16 py-8"
            >
              <div className="flex flex-col gap-8">
                <label htmlFor={fromId} className="font-display text-ink">
                  Available From
                </label>
                <input
                  id={fromId}
                  type="date"
                  value={range.start}
                  onChange={(event) =>
                    setDateRange(index, { ...range, start: event.target.value })
                  }
                  className={INPUT_CLASSES}
                />
              </div>
              <div className="flex flex-col gap-8">
                <label htmlFor={untilId} className="font-display text-ink">
                  Available Until
                </label>
                <input
                  id={untilId}
                  type="date"
                  value={range.end}
                  onChange={(event) =>
                    setDateRange(index, { ...range, end: event.target.value })
                  }
                  className={INPUT_CLASSES}
                />
              </div>
              {canRemoveRange ? (
                <PixelButton
                  variant="danger"
                  label="Remove range"
                  ariaLabel={`Remove availability range ${index + 1}`}
                  onClick={() => removeDateRange(index)}
                />
              ) : null}
            </div>
          );
        })}
        <PixelButton
          variant="secondary"
          label="Add range"
          ariaLabel="Add availability range"
          onClick={addDateRange}
        />
      </fieldset>

      {/* 10. Save. */}
      <div className="flex flex-col gap-8">
        {!canSave ? (
          <p className="font-body text-muted">
            Choose a budget and a group role to save your traveller.
          </p>
        ) : null}
        <PixelButton
          variant="primary"
          type="button"
          label={submitting ? "SAVING…" : "SAVE CHARACTER"}
          disabled={!canSave || submitting}
          onClick={() => {
            void handleSave();
          }}
        />
        {submitError !== null ? (
          <p role="alert" className="font-body text-danger">
            {submitError}
          </p>
        ) : null}
        <p role="status" aria-live="polite" className="font-body text-muted">
          {savedOnce && sessionCharacter !== null
            ? "Traveller saved and shared with your party."
            : ""}
        </p>
      </div>
    </section>
  );
}

export default CharacterCreator;
