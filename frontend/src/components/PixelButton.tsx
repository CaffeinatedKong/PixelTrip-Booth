/**
 * PixelButton — placeholder primitive shell (Foundation, Task 5).
 *
 * A blocky 8-bit action button with token-based variants and accessible pressed,
 * disabled, and focus states. Styling uses design-token utility classes only —
 * never raw hex or arbitrary values.
 */
import { forwardRef, type ReactElement } from "react";

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
  /** Optional accessible name when the visible label needs extra context. */
  ariaLabel?: string;
  /** Exposes toggle-like selection state to assistive technology. */
  ariaPressed?: boolean;
  /** Button type for forms; defaults to a non-submitting action. */
  type?: "button" | "submit";
  /** Optional token-based utility classes for layout composition. */
  className?: string;
}

const VARIANT_CLASSES: Record<PixelButtonVariant, string> = {
  primary: "bg-primary text-bg",
  secondary: "bg-bg-alt text-ink",
  option: "bg-accent text-ink",
  danger: "bg-danger text-bg",
};

export const PixelButton = forwardRef<HTMLButtonElement, PixelButtonProps>(
  function PixelButton(
    {
      label,
      variant = "primary",
      onClick,
      disabled = false,
      ariaLabel,
      ariaPressed,
      className = "",
      type = "button",
    },
    ref,
  ): ReactElement {
    return (
      <button
        ref={ref}
        type={type}
        onClick={onClick}
        disabled={disabled}
        aria-label={ariaLabel}
        aria-pressed={ariaPressed}
        className={`font-display border-2 border-ink px-16 py-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg motion-reduce:transition-none ${VARIANT_CLASSES[variant]} disabled:bg-muted disabled:text-bg-alt ${className}`}
      >
        {label}
      </button>
    );
  },
);

export default PixelButton;
