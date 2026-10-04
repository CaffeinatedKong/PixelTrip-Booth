/**
 * PreferenceFields — the travel-preference inputs of the character creator.
 *
 * Presentational only: every value arrives via props and every change is raised
 * through a callback. There is no data fetching, no persistence, and no service
 * import. The one piece of local state (`useState`) is the uncommitted text of the
 * "add hard constraint" field — pure UI state for an input that has not been
 * committed yet, never stored or sent anywhere.
 *
 * Renders, in order:
 *   1. A numeric "ADVENTURE FUNDS" (budget) input.
 *   2. An "ORIGIN" text input.
 *   3. A repeatable "HARD CONSTRAINTS" list with add/remove controls.
 *   4. One or more availability ranges, each an "Available From" / "Available
 *      Until" date pair, with add/remove-range controls (at least one range is
 *      always kept).
 *
 * Every input has a programmatic `<label htmlFor>` tied to a unique input id.
 * Styling uses design-token utility classes only — never raw hex or arbitrary
 * values.
 */
import { useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";

import { type DateRange } from "../types";

export interface PreferenceFieldsProps {
  /** Raw budget text (controlled). */
  budgetText: string;
  /** Raised with the new budget text on change. */
  onBudgetChange: (text: string) => void;
  /** Origin location text (controlled). */
  origin: string;
  /** Raised with the new origin text on change. */
  onOriginChange: (text: string) => void;
  /** The committed hard-constraint lines. */
  hardConstraints: readonly string[];
  /** Raised with a new constraint when the user adds one. */
  onAddConstraint: (text: string) => void;
  /** Raised with the index of a constraint to remove. */
  onRemoveConstraint: (index: number) => void;
  /** One or more availability ranges (at least one is always present). */
  availableDates: readonly DateRange[];
  /** Raised with the index and the updated range when a date changes. */
  onDateRangeChange: (index: number, range: DateRange) => void;
  /** Raised to append a new (empty) availability range. */
  onAddDateRange: () => void;
  /** Raised with the index of an availability range to remove. */
  onRemoveDateRange: (index: number) => void;
}

const INPUT_CLASSES =
  "font-body text-ink bg-bg border-2 border-muted px-16 py-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

export function PreferenceFields({
  budgetText,
  onBudgetChange,
  origin,
  onOriginChange,
  hardConstraints,
  onAddConstraint,
  onRemoveConstraint,
  availableDates,
  onDateRangeChange,
  onAddDateRange,
  onRemoveDateRange,
}: PreferenceFieldsProps): ReactElement {
  // UI-only: the uncommitted text for the "add constraint" field. Nothing is
  // stored or sent — it is cleared once committed via onAddConstraint.
  const [newConstraint, setNewConstraint] = useState("");

  const commitConstraint = (): void => {
    const trimmed = newConstraint.trim();
    if (trimmed.length === 0) {
      return;
    }
    onAddConstraint(trimmed);
    setNewConstraint("");
  };

  const canRemoveRange = availableDates.length > 1;

  return (
    <div className="flex flex-col gap-24">
      {/* 1. Budget --------------------------------------------------------- */}
      <div className="flex flex-col gap-8">
        <label htmlFor="pref-budget" className="font-display text-ink">
          ADVENTURE FUNDS
        </label>
        <input
          id="pref-budget"
          type="number"
          min={0}
          value={budgetText}
          onChange={(event) => onBudgetChange(event.target.value)}
          placeholder="1500"
          className={INPUT_CLASSES}
        />
      </div>

      {/* 2. Origin --------------------------------------------------------- */}
      <div className="flex flex-col gap-8">
        <label htmlFor="pref-origin" className="font-display text-ink">
          ORIGIN
        </label>
        <input
          id="pref-origin"
          type="text"
          value={origin}
          onChange={(event) => onOriginChange(event.target.value)}
          placeholder="SIN"
          autoComplete="off"
          className={INPUT_CLASSES}
        />
      </div>

      {/* 3. Hard constraints ---------------------------------------------- */}
      <fieldset className="flex flex-col gap-8">
        <legend className="font-display text-ink mb-8">HARD CONSTRAINTS</legend>

        {hardConstraints.length > 0 ? (
          <ul className="flex flex-col gap-8">
            {hardConstraints.map((constraint, index) => (
              <li
                key={`${constraint}-${index}`}
                className="flex items-center gap-8"
              >
                <span className="font-body text-ink grow">{constraint}</span>
                <PixelButton
                  variant="danger"
                  label="Remove"
                  ariaLabel={`Remove constraint ${constraint}`}
                  onClick={() => onRemoveConstraint(index)}
                />
              </li>
            ))}
          </ul>
        ) : (
          <p className="font-body text-muted">No hard constraints yet.</p>
        )}

        <div className="flex items-center gap-8">
          <label htmlFor="pref-new-constraint" className="sr-only">
            Add a hard constraint
          </label>
          <input
            id="pref-new-constraint"
            type="text"
            value={newConstraint}
            onChange={(event) => setNewConstraint(event.target.value)}
            placeholder="no red-eye flights"
            autoComplete="off"
            className={`${INPUT_CLASSES} grow`}
          />
          <PixelButton
            variant="secondary"
            label="Add"
            ariaLabel="Add hard constraint"
            onClick={commitConstraint}
          />
        </div>
      </fieldset>

      {/* 4. Availability ranges ------------------------------------------- */}
      <fieldset className="flex flex-col gap-16">
        <legend className="font-display text-ink mb-8">AVAILABILITY</legend>

        {availableDates.map((range, index) => {
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
                    onDateRangeChange(index, {
                      ...range,
                      start: event.target.value,
                    })
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
                    onDateRangeChange(index, {
                      ...range,
                      end: event.target.value,
                    })
                  }
                  className={INPUT_CLASSES}
                />
              </div>

              {canRemoveRange ? (
                <PixelButton
                  variant="danger"
                  label="Remove range"
                  ariaLabel={`Remove availability range ${index + 1}`}
                  onClick={() => onRemoveDateRange(index)}
                />
              ) : null}
            </div>
          );
        })}

        <PixelButton
          variant="secondary"
          label="Add range"
          ariaLabel="Add availability range"
          onClick={onAddDateRange}
        />
      </fieldset>
    </div>
  );
}

export default PreferenceFields;
