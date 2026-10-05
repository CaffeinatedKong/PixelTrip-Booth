/**
 * Render test for PartyLobby (entry screen).
 *
 * Verifies the entry screen presents the adventurer-name field and both the
 * Create Party and Join Party actions, and that submitting raises the callbacks
 * with the entered values. Purely presentational — no service layer involved.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PartyLobby } from "./PartyLobby";

describe("PartyLobby", () => {
  it("renders the adventurer-name field and both actions", () => {
    render(
      <PartyLobby
        view="entry"
        onCreateParty={vi.fn()}
        onJoinParty={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Adventurer name")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Create Party" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Join Party" }),
    ).toBeInTheDocument();
  });

  it("raises onCreateParty with the room and adventurer names", () => {
    const onCreateParty = vi.fn();
    render(
      <PartyLobby
        view="entry"
        onCreateParty={onCreateParty}
        onJoinParty={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("Adventurer name"), {
      target: { value: "Aria" },
    });
    fireEvent.change(screen.getByLabelText("Party name"), {
      target: { value: "The Wandering Party" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Party" }));

    expect(onCreateParty).toHaveBeenCalledWith("The Wandering Party", "Aria");
  });

  it("raises onJoinParty with the code and adventurer name", () => {
    const onJoinParty = vi.fn();
    render(
      <PartyLobby
        view="entry"
        onCreateParty={vi.fn()}
        onJoinParty={onJoinParty}
      />,
    );

    fireEvent.change(screen.getByLabelText("Adventurer name"), {
      target: { value: "Aria" },
    });
    fireEvent.change(screen.getByLabelText("Party code"), {
      target: { value: "ABC123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Join Party" }));

    expect(onJoinParty).toHaveBeenCalledWith("ABC123", "Aria");
  });
});
