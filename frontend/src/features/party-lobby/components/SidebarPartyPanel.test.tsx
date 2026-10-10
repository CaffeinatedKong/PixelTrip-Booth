import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SidebarPartyPanel, inviteLink } from "./SidebarPartyPanel";

const writeText = vi.fn();

beforeEach(() => {
  writeText.mockReset().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
});

const show = (roomCode: string | null = "TVJ49F"): void => {
  render(<SidebarPartyPanel members={[]} capacity={2} roomCode={roomCode} />);
};

describe("SidebarPartyPanel invite", () => {
  it("builds a link that carries the room code", () => {
    expect(inviteLink("TVJ49F", "https://trip.example")).toBe(
      "https://trip.example/?code=TVJ49F",
    );
  });

  it("copies the invite link and confirms it on the button", async () => {
    show();
    fireEvent.click(screen.getByRole("button", { name: "COPY INVITE LINK" }));

    expect(await screen.findByRole("button", { name: "LINK COPIED!" })).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/?code=TVJ49F`);
    expect(screen.getByRole("status")).toHaveTextContent("Invite link copied");
  });

  it("copies just the room code", async () => {
    show();
    fireEvent.click(screen.getByRole("button", { name: "Copy room code" }));

    expect(await screen.findByText("Room code copied.")).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith("TVJ49F");
  });

  it("says so when the browser refuses the clipboard", async () => {
    writeText.mockRejectedValue(new Error("denied"));
    show();
    fireEvent.click(screen.getByRole("button", { name: "COPY INVITE LINK" }));

    expect(
      await screen.findByText("Could not copy. Share the room code above instead."),
    ).toBeInTheDocument();
  });

  it("offers nothing to copy before there is a room code", () => {
    show(null);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("No room code yet")).toBeInTheDocument();
  });
});
