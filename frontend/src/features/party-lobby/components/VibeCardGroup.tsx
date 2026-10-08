"use client";

/**
 * VibeCardGroup — the single reusable selectable-card group used across the whole
 * character/preference questionnaire AND the destination picker, so every choice
 * on the screen looks identical.
 *
 * Each option renders as a card: an 8-bit blue panel with a gold border + gold
 * title (emoji + label) and a readable white description. The SELECTED card flips
 * to a gold fill with dark ink text, so the chosen option is obvious.
 *
 * Supports both selection modes via `mode`:
 * - `"multi"` (default): any number selected; `onToggle(id)` adds/removes.
 * - `"single"`: exactly one; the same `onToggle(id)` fires and the parent keeps
 *   one id. (Re-selecting the active one is a parent decision.)
 *
 * Presentational only: no data fetching, no persistence. Token styling only.
 */
import type { ReactElement } from "react";

import type { CharacterOption } from "../lib/characterOptions";

export interface VibeCardGroupProps {
  /** Group heading rendered as the fieldset legend. */
  legend: string;
  /** Selectable options; each carries a stable id, label, optional icon + description. */
  options: readonly CharacterOption[];
  /** Ids of the currently selected options. */
  selectedIds: readonly string[];
  /** Raised when a card is activated. */
  onToggle: (id: string) => void;
  /** Selection semantics for assistive tech + visuals. Defaults to "multi". */
  mode?: "single" | "multi";
}

export function VibeCardGroup({
  legend,
  options,
  selectedIds,
  onToggle,
  mode = "multi",
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
              aria-label={mode === "single" ? option.label : undefined}
              onClick={() => onToggle(option.id)}
              className={`flex flex-col gap-8 border-2 p-16 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg motion-reduce:transition-none ${
                selected
                  ? "border-ink bg-accent text-ink"
                  : "border-accent bg-bg-alt text-ink"
              }`}
            >
              <span
                className={`flex items-center gap-8 font-display ${
                  selected ? "text-ink" : "text-accent"
                }`}
              >
                {option.icon ? (
                  <span aria-hidden className="text-xl leading-none">
                    {option.icon}
                  </span>
                ) : null}
                {option.label}
              </span>
              {option.description ? (
                <span className="font-body text-ink">{option.description}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export default VibeCardGroup;
