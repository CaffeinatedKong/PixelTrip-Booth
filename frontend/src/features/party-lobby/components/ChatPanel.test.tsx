/**
 * Render tests for ChatPanel (local-only party chat).
 *
 * Verifies the honest "local only" notice is present, that typing + Send appends
 * the viewer's message as a user bubble, and that an empty/whitespace send does
 * nothing. Purely presentational local state — no service layer involved.
 */
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatPanel } from "./ChatPanel";

describe("ChatPanel", () => {
  it("shows the honest local-only notice", () => {
    render(<ChatPanel viewerDisplayName="Aria" />);
    expect(
      screen.getByText(/local to your screen for now/i),
    ).toBeInTheDocument();
  });

  it("appends the viewer's message as a user bubble on Send", () => {
    render(<ChatPanel viewerDisplayName="Aria" />);

    const input = screen.getByLabelText(/message the party/i);
    fireEvent.change(input, { target: { value: "Hello party" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    const list = screen.getByRole("list", { name: "Party chat messages" });
    expect(within(list).getByText("Hello party")).toBeInTheDocument();
    // The viewer's own line is labelled with "(you)".
    expect(within(list).getByText(/Aria \(you\)/)).toBeInTheDocument();
    // Input clears after sending.
    expect(input).toHaveValue("");
  });

  it("does nothing when sending an empty or whitespace-only draft", () => {
    render(<ChatPanel viewerDisplayName="Aria" />);

    const list = screen.getByRole("list", { name: "Party chat messages" });
    const before = within(list).getAllByRole("listitem").length;

    // Empty send.
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));
    // Whitespace send.
    fireEvent.change(screen.getByLabelText(/message the party/i), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(within(list).getAllByRole("listitem")).toHaveLength(before);
  });
});
