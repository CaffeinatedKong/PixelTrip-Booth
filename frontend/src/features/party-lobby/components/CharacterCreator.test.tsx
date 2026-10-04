/**
 * Render tests for CharacterCreator (local-only 8-bit creator).
 *
 * Verifies the appearance selection drives the preview sprite key, that Save is
 * gated (with a hint) until appearance + outfit + accessory are chosen and then
 * shows the honest local-only confirmation, and that multi-select toggles on and
 * off. Purely presentational local state — no service layer involved.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CharacterCreator } from "./CharacterCreator";

/** The sprite preview is the only [data-sprite-key] element with the lg size. */
function previewSpriteKey(): string | null {
  const sprite = document.querySelector("[data-sprite-key]");
  return sprite?.getAttribute("data-sprite-key") ?? null;
}

describe("CharacterCreator", () => {
  it("updates the preview sprite key when an appearance is selected", () => {
    render(<CharacterCreator viewerDisplayName="Aria" />);

    // Default placeholder before any choice.
    expect(previewSpriteKey()).toBe("none");

    fireEvent.click(screen.getByRole("button", { name: "Ranger" }));
    expect(previewSpriteKey()).toBe("ranger");

    fireEvent.click(screen.getByRole("button", { name: "Scholar" }));
    expect(previewSpriteKey()).toBe("scholar");
  });

  it("gates Save until appearance, outfit, and accessory are chosen", () => {
    render(<CharacterCreator viewerDisplayName="Aria" />);

    const save = screen.getByRole("button", { name: /save character locally/i });
    expect(save).toBeDisabled();
    expect(
      screen.getByText(/choose an appearance, outfit, and accessory/i),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Explorer" }));
    fireEvent.click(screen.getByRole("button", { name: "Casual" }));
    expect(save).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Map" }));
    expect(save).toBeEnabled();

    fireEvent.click(save);
    // The live status region shows the local-only confirmation after saving.
    expect(screen.getByRole("status")).toHaveTextContent(
      /character saved on your screen only/i,
    );
  });

  it("toggles a multi-select interest on and off via aria-pressed", () => {
    render(<CharacterCreator viewerDisplayName="Aria" />);

    const food = screen.getByRole("button", { name: "Food" });
    expect(food).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(food);
    expect(food).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(food);
    expect(food).toHaveAttribute("aria-pressed", "false");
  });
});
