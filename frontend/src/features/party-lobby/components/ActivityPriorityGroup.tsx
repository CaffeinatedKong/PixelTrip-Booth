/**
 * ActivityPriorityGroup — a multi-select activity group with a per-activity priority control.
 *
 * Presentational only: it receives its options and the currently selected
 * {@link ActivityDraft}s via props and raises changes through `onToggle` and
 * `onPriorityChange`. There is no data fetching, no persistence, and no service
 * import.
 *
 * Each option renders as a shared {@link PixelButton} (`variant="option"`) that
 * toggles the activity on/off, exposing its selected state to assistive technology
 * via `aria-pressed` (the activity `name` corresponds to the option id). WHERE an
 * activity is selected, an additional two-state priority control ("Must have" /
 * "Optional") is rendered, each button reflecting the current priority via
 * `aria-pressed`.
 *
 * Produces/consumes `ActivityDraft` objects `{ name, priority }`. Styling uses
 * design-token utility classes only — never raw hex or arbitrary values.
 */
import { type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";

import { type CharacterOption } from "../lib/characterOptions";
import { type ActivityDraft } from "../types";

export interface ActivityPriorityGroupProps {
  /** Group label rendered in the fieldset's `<legend>`. */
  legend: string;
  /** The selectable activities; each becomes one toggle button. */
  options: readonly CharacterOption[];
  /** The currently selected activities together with their priority. */
  selected: readonly ActivityDraft[];
  /** Raised with the activity name (option id) when the user toggles an activity. */
  onToggle: (name: string) => void;
  /** Raised with the activity name and the chosen priority for a selected activity. */
  onPriorityChange: (name: string, priority: "must_have" | "optional") => void;
}

export function ActivityPriorityGroup({
  legend,
  options,
  selected,
  onToggle,
  onPriorityChange,
}: ActivityPriorityGroupProps): ReactElement {
  return (
    <fieldset className="flex flex-col gap-8">
      <legend className="font-display text-ink mb-8">{legend}</legend>
      <div className="flex flex-col gap-8">
        {options.map((option) => {
          const draft = selected.find((activity) => activity.name === option.id);
          const isSelected = draft !== undefined;

          return (
            <div key={option.id} className="flex flex-wrap items-center gap-8">
              <PixelButton
                variant="option"
                label={option.label}
                ariaPressed={isSelected}
                onClick={() => onToggle(option.id)}
              />
              {draft !== undefined && (
                <div className="flex flex-wrap gap-8">
                  <PixelButton
                    variant="option"
                    label="Must have"
                    ariaLabel={`${option.label}: Must have`}
                    ariaPressed={draft.priority === "must_have"}
                    onClick={() => onPriorityChange(option.id, "must_have")}
                  />
                  <PixelButton
                    variant="option"
                    label="Optional"
                    ariaLabel={`${option.label}: Optional`}
                    ariaPressed={draft.priority === "optional"}
                    onClick={() => onPriorityChange(option.id, "optional")}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}

export default ActivityPriorityGroup;
