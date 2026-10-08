"use client";

/**
 * VibeCardGroup — multi-select group of larger "vibe" cards with a title and a
 * one-line description, used for destination vibes ("Where do you feel like
 * going?"). Each card is a selectable button whose pressed state is exposed via
 * `aria-pressed`; toggles are raised to the parent via `onToggle`.
 *
 * Presentational only: no data fetching, no persistence. Styling uses design-token
 * utility classes only — never raw hex or arbitrary magic values. Cards lay out in
 * a single column on mobile and two columns from the small breakpoint up.
 */
import type { ReactElement } from "react";

import type { CharacterOption } from "../lib/characterOptions";

export interface VibeCardGroupProps {
  /** Group heading rendered as the fieldset legend. */
  legend: string;
  /** Selectable options; each carries a stable id, label, and optional description. */
  options: readonly CharacterOption[];
  /** Ids of the currently selected options. */
  selectedIds: readonly string[];
  /** Raised when a card is activated (parent decides add vs remove). */
  onToggle: (id: string) => void;
}

export function VibeCardGroup({
  legend,
  options,
  selectedIds,
  onToggle,
}: VibeCardGroupProps): ReactElement {
  return (
    <fieldset className="flex flex-col gap-8">
      <legend className="font-display text-ink mb-8">{legend}</legend>
      <div className="grid grid-cols-1 gap-8 sm:grid-cols-2">
        {options.map((option) => {
          const selected = selectedIds.includes(option.id);
          return (
            <button
              key={option.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onToggle(option.id)}
              className={`flex flex-col gap-8 border-2 p-16 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg motion-reduce:transition-none ${
                selected
                  ? "border-accent bg-bg-alt text-ink"
                  : "border-muted bg-bg text-ink"
              }`}
            >
              <span className="font-display">{option.label}</span>
              {option.description ? (
                <span className="font-body text-muted">
                  {option.description}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export default VibeCardGroup;
