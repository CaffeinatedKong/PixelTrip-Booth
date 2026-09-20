/**
 * CharacterSprite — placeholder primitive shell (Foundation, Task 5).
 *
 * Renders an 8-bit character avatar. Typed shell only: it reserves the sprite
 * slot with an accessible label and a token-styled box sized by an integer
 * factor. Real sprite rendering from character data (per `pixel-design-system.md`)
 * is added later. Styling uses design-token utility classes only.
 */
import type { ReactElement } from "react";

export type CharacterSpriteSize = "sm" | "md" | "lg";

export interface CharacterSpriteProps {
  /** Identifier for the sprite/appearance to render (resolved later). */
  spriteKey: string;
  /** Accessible label describing the character. */
  label: string;
  /** Integer-scaled sprite size. Defaults to `md`. */
  size?: CharacterSpriteSize;
}

const SIZE_CLASSES: Record<CharacterSpriteSize, string> = {
  sm: "w-16 h-16",
  md: "w-24 h-24",
  lg: "w-32 h-32",
};

export function CharacterSprite({
  spriteKey,
  label,
  size = "md",
}: CharacterSpriteProps): ReactElement {
  return (
    <div
      role="img"
      aria-label={label}
      data-sprite-key={spriteKey}
      className={`image-rendering-pixelated bg-bg-alt border-2 border-ink ${SIZE_CLASSES[size]}`}
    />
  );
}

export default CharacterSprite;
