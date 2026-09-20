/**
 * PixelButton — placeholder primitive shell (Foundation, Task 5).
 *
 * A blocky 8-bit action button. This is a typed shell only: it renders a minimal
 * <button> styled with design tokens and is NOT the full feature implementation
 * (no pressed/hover animation, no icon slots yet). Filled in later against
 * `pixel-design-system.md`. Styling uses design-token utility classes only —
 * never raw hex or arbitrary values.
 */
import type { ReactElement } from "react";

export type PixelButtonVariant = "primary" | "secondary" | "option" | "danger";

export interface PixelButtonProps {
  /** Visible, accessible button label. */
  label: string;
  /** Visual role of the button. Defaults to `primary`. */
  variant?: PixelButtonVariant;
  /** Click handler. */
  onClick?: () => void;
  /** Disables interaction when true. */
  disabled?: boolean;
}

const VARIANT_CLASSES: Record<PixelButtonVariant, string> = {
  primary: "bg-primary text-bg",
  secondary: "bg-bg-alt text-ink",
  option: "bg-accent text-ink",
  danger: "bg-danger text-bg",
};

export function PixelButton({
  label,
  variant = "primary",
  onClick,
  disabled = false,
}: PixelButtonProps): ReactElement {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`font-display px-16 py-8 border-2 border-ink ${VARIANT_CLASSES[variant]} disabled:bg-muted disabled:text-bg-alt`}
    >
      {label}
    </button>
  );
}

export default PixelButton;
