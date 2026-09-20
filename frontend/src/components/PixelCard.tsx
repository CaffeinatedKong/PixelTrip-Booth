/**
 * PixelCard — placeholder primitive shell (Foundation, Task 5).
 *
 * A blocky RPG panel with a solid border. Typed shell only: renders an optional
 * title and its children in a minimally styled panel. The concrete card variants
 * (recommendation / voting / decision-summary) from `pixel-design-system.md` are
 * added later. Styling uses design-token utility classes only.
 */
import type { ReactElement, ReactNode } from "react";

export interface PixelCardProps {
  /** Optional card heading rendered in the display font. */
  title?: string;
  /** Card body content. */
  children?: ReactNode;
}

export function PixelCard({ title, children }: PixelCardProps): ReactElement {
  return (
    <section className="bg-bg-alt text-ink border-2 border-ink p-16">
      {title ? <h3 className="font-display mb-8">{title}</h3> : null}
      <div className="font-body">{children}</div>
    </section>
  );
}

export default PixelCard;
