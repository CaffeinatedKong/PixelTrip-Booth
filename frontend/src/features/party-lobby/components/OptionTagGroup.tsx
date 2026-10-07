/**
 * OptionTagGroup — multi-select pixel-tag group (Lobby / Character Creation).
 *
 * Presentational only: renders a `fieldset`/`legend` with one shared `PixelButton`
 * (`variant="option"`) per option. Selection membership is reflected through
 * `aria-pressed`, and toggles are raised to the parent via `onToggle`. No data
 * fetching, no persistence. Reused for trip priorities, destinations, and activities.
 *
 * Token styling only — spacing and layout utilities map to design-system tokens;
 * no raw hex or arbitrary magic values.
 */
import type { ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";

import type { CharacterOption } from "../lib/characterOptions";

export interface OptionTagGroupProps {
  /** Group heading rendered as the fieldset legend. */
  legend: string;
  /** Selectable options; each must carry a stable id and label. */
  options: readonly CharacterOption[];
  /** Ids of the currently selected options. */
  selectedIds: readonly string[];
  /** Raised when an option tag is activated (parent decides add vs remove). */
  onToggle: (id: string) => void;
}

/** Multi-select group of pixel tags backed by the shared `PixelButton`. */
export function OptionTagGroup({
  legend,
  options,
  selectedIds,
  onToggle,
}: OptionTagGroupProps): ReactElement {
  return (
    <fieldset className="border-2 border-ink p-16">
      <legend className="font-display px-8 text-ink">{legend}</legend>
      <div className="flex flex-wrap gap-8">
        {options.map((option) => (
          <PixelButton
            key={option.id}
            label={option.label}
            variant="option"
            ariaPressed={selectedIds.includes(option.id)}
            onClick={() => onToggle(option.id)}
          />
        ))}
      </div>
    </fieldset>
  );
}

export default OptionTagGroup;
