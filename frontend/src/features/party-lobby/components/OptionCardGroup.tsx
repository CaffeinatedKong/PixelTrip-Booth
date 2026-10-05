/**
 * OptionCardGroup — a single-select group of pixel option cards.
 *
 * Presentational only: it receives its options and the currently selected id via
 * props and raises the chosen id through `onSelect`. There is no data fetching,
 * no persistence, and no service import. Each option renders as a shared
 * {@link PixelButton} (`variant="option"`) whose pressed state is exposed to
 * assistive technology via `aria-pressed`.
 *
 * Reused across the character creator for Archetype, Outfit, Accessory, Palette,
 * and Travel Style single-select groups. Styling uses design-token utility
 * classes only — never raw hex or arbitrary values.
 */
import { type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";

import { type CharacterOption } from "../lib/characterOptions";

export interface OptionCardGroupProps {
  /** Group label rendered in the fieldset's `<legend>`. */
  legend: string;
  /** The selectable options; each becomes one option button. */
  options: readonly CharacterOption[];
  /** The id of the currently selected option, or `null` when none is chosen. */
  selectedId: string | null;
  /** Raised with the option id when the user selects an option. */
  onSelect: (id: string) => void;
}

export function OptionCardGroup({
  legend,
  options,
  selectedId,
  onSelect,
}: OptionCardGroupProps): ReactElement {
  return (
    <fieldset className="flex flex-col gap-8">
      <legend className="font-display text-ink mb-8">{legend}</legend>
      <div className="flex flex-wrap gap-8">
        {options.map((option) => (
          <PixelButton
            key={option.id}
            variant="option"
            label={option.label}
            ariaPressed={selectedId === option.id}
            onClick={() => onSelect(option.id)}
          />
        ))}
      </div>
    </fieldset>
  );
}

export default OptionCardGroup;
