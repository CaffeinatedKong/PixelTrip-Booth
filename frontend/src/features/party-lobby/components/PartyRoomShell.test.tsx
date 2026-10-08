/**
 * Render tests for PartyRoomShell (the honest 6-stage pipeline shell).
 *
 * Verifies the stepper lists all six stages, that the SETUP stage renders the
 * real waiting-room content (room code + roster) with SETUP marked current, and
 * that a non-SETUP planningStage renders the honest placeholder instead of any
 * setup content. Purely presentational — no service layer involved.
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PlanningStage, RoomMember, RoomSession } from "@/types";

import { PartyRoomShell } from "./PartyRoomShell";

function makeMember(overrides: Partial<RoomMember> = {}): RoomMember {
  return {
    id: "member-1",
    roomId: "room-1",
    guestId: "guest-1",
    displayName: "Aria",
    role: "owner",
    stageReady: false,
    ...overrides,
  };
}

function makeSession(planningStage: PlanningStage): RoomSession {
  return {
    room: {
      id: "room-1",
      roomCode: "ABC123",
      name: "The Wandering Party",
      status: "active",
      planningStage,
    },
    member: makeMember(),
    guest: { id: "guest-1", displayName: "Aria", avatarUrl: null },
    character: null,
    travelPreferences: null,
  };
}

describe("PartyRoomShell", () => {
  it("renders the six-stage stepper with SETUP current and shows the real setup content", () => {
    render(
      <PartyRoomShell
        session={makeSession("setup")}
        members={[makeMember()]}
        copied={false}
        onCopyCode={vi.fn()}
        onLeave={vi.fn()}
      />,
    );

    // All six stages are listed.
    const stepper = screen.getByRole("list", { name: "Planning stages" });
    expect(within(stepper).getAllByRole("listitem")).toHaveLength(6);

    // SETUP is the current step.
    const current = within(stepper).getByText("Gather the party").closest("li");
    expect(current).toHaveAttribute("aria-current", "step");

    // Real setup content is shown: the room code and the live roster.
    expect(screen.getByTestId("room-code")).toHaveTextContent("ABC123");
    const roster = screen.getByRole("list", { name: "Party members" });
    expect(within(roster).getByText("Aria")).toBeInTheDocument();

    // No placeholder for the real stage.
    expect(screen.queryByTestId("stage-placeholder")).not.toBeInTheDocument();

    // The local-only character creator and chat panel render alongside setup.
    expect(
      screen.getByRole("list", { name: "Party chat messages" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /save character/i }),
    ).toBeInTheDocument();
  });

  it("gives the sidebar's quest progress its own name, distinct from the stepper", () => {
    render(
      <PartyRoomShell
        session={makeSession("setup")}
        members={[makeMember()]}
        copied={false}
        onCopyCode={vi.fn()}
        onLeave={vi.fn()}
      />,
    );

    // Both six-stage lists are on screen in SETUP; each must be addressable by name.
    const stepper = screen.getByRole("list", { name: "Planning stages" });
    const sidebar = screen.getByRole("list", { name: "Quest progress" });

    expect(stepper).not.toBe(sidebar);
    expect(within(sidebar).getAllByRole("listitem")).toHaveLength(6);
    expect(
      within(sidebar).getByText("Gather the party").closest("li"),
    ).toHaveAttribute("aria-current", "step");
  });

  it("renders an honest placeholder for a non-setup stage and no setup content", () => {
    render(
      <PartyRoomShell
        session={makeSession("discover")}
        members={[makeMember()]}
        copied={false}
        onCopyCode={vi.fn()}
        onLeave={vi.fn()}
      />,
    );

    // The placeholder is shown for the stubbed stage.
    const placeholder = screen.getByTestId("stage-placeholder");
    expect(placeholder).toBeInTheDocument();
    expect(placeholder).toHaveTextContent(/isn't open yet/i);

    // No real setup content leaks through.
    expect(screen.queryByTestId("room-code")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("list", { name: "Party members" }),
    ).not.toBeInTheDocument();

    // Neither the chat panel nor the character creator render off-setup.
    expect(
      screen.queryByRole("list", { name: "Party chat messages" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /save character/i }),
    ).not.toBeInTheDocument();

    // DISCOVER is marked current in the stepper.
    const stepper = screen.getByRole("list", { name: "Planning stages" });
    const current = within(stepper)
      .getByText("Choose the destination")
      .closest("li");
    expect(current).toHaveAttribute("aria-current", "step");
  });
});
