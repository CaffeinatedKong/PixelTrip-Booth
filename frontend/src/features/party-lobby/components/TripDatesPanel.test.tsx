import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/errors";
import type { TripDates } from "@/services/tripDates.contract";

import {
  addDays,
  stayPreview,
  tripDatesProblem,
} from "../lib/tripDates";
import { TripDatesPanel } from "./TripDatesPanel";

const changeDates = vi.fn();
const startRun = vi.fn();
vi.mock("@/services", () => ({
  getServices: () => ({
    tripDates: { changeDates },
    run: { startRun },
  }),
}));

// Far in the future so "not in the past" never depends on the day the test runs.
const DATES: TripDates = {
  destination: "Kyoto, Japan",
  tripDays: 6,
  tripStart: "2099-03-18",
  tripEnd: "2099-03-23",
  whyThisLong: "Six days covers the temples and a day trip to Nara.",
  windows: [{ start: "2099-03-10", end: "2099-04-08" }],
  minDays: 2,
  maxDays: 14,
  dailyCostSgd: 140,
  budgetLimit: 2400,
  canChange: true,
  lockedReason: null,
};

const leader = { roomId: "room-1", memberId: "m1", isOwner: true };

beforeEach(() => {
  changeDates.mockReset().mockResolvedValue(DATES);
  startRun.mockReset().mockResolvedValue(undefined);
});

describe("trip date rules", () => {
  it("adds calendar days across a month end", () => {
    expect(addDays("2099-03-30", 3)).toBe("2099-04-02");
  });

  it("accepts dates inside a shared window and explains the rest", () => {
    expect(tripDatesProblem(DATES, 6, "2099-03-18", "2099-01-01")).toBeNull();
    expect(tripDatesProblem(DATES, 6, "2099-04-05", "2099-01-01")).toMatch(
      /outside when the whole party is free/,
    );
    expect(tripDatesProblem(DATES, 20, "2099-03-18", "2099-01-01")).toBe(
      "The trip must be 2 to 14 days long.",
    );
    expect(tripDatesProblem(DATES, 6, "2099-03-18", "2099-03-20")).toBe(
      "The trip cannot start in the past.",
    );
  });

  it("previews the stay against the budget", () => {
    expect(stayPreview(DATES, 6)).toEqual({ stay: 840, left: 1560, tight: false });
    expect(stayPreview(DATES, 12)).toEqual({ stay: 1680, left: 720, tight: true });
    expect(stayPreview({ ...DATES, dailyCostSgd: null }, 6)).toBeNull();
  });
});

describe("TripDatesPanel", () => {
  it("shows 'Not set yet' before a destination is chosen", () => {
    render(<TripDatesPanel />);
    expect(screen.getByTestId("trip-dates-panel")).toHaveTextContent("Not set yet");
  });

  it("shows the trip's length and dates, with CHANGE for the leader only", () => {
    const { rerender } = render(<TripDatesPanel dates={DATES} {...leader} />);
    expect(screen.getByTestId("trip-dates-panel")).toHaveTextContent(
      /6 DAYS · Wed 18 – Mon 23 Mar/,
    );
    expect(
      screen.getByRole("button", { name: "Change trip dates" }),
    ).toBeInTheDocument();

    rerender(<TripDatesPanel dates={DATES} {...leader} isOwner={false} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("The party leader can change these.")).toBeInTheDocument();
  });

  it("says why the dates are locked once a flight is chosen", () => {
    render(
      <TripDatesPanel
        dates={{ ...DATES, canChange: false, lockedReason: "The flight is already locked." }}
        {...leader}
      />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("The flight is already locked.")).toBeInTheDocument();
  });
});

describe("TripDatesDialog (opened from the panel)", () => {
  const open = (): void => {
    render(<TripDatesPanel dates={DATES} {...leader} />);
    fireEvent.click(screen.getByRole("button", { name: "Change trip dates" }));
  };

  it("opens focused on the start date and closes on Escape without saving", () => {
    open();
    const dialog = screen.getByRole("dialog", { name: "CHANGE TRIP DATES" });
    expect(screen.getByLabelText("Start date")).toHaveFocus();

    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(changeDates).not.toHaveBeenCalled();
  });

  it("updates the end date and the stay cost as the length changes", () => {
    open();
    expect(screen.getByRole("button", { name: "SAVE AND SEARCH FLIGHTS" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "One day longer" }));

    expect(screen.getByTestId("trip-days")).toHaveTextContent("7 DAYS");
    const preview = screen.getByTestId("trip-dates-preview");
    expect(preview).toHaveTextContent("Wed 18 Mar – Tue 24 Mar");
    expect(preview).toHaveTextContent("about SGD 980 per person");
    expect(preview).toHaveTextContent("leaving about SGD 1,420");
  });

  it("explains dates outside the party's free window under the field", () => {
    open();
    fireEvent.change(screen.getByLabelText("Start date"), {
      target: { value: "2099-04-06" },
    });
    fireEvent.blur(screen.getByLabelText("Start date"));

    expect(screen.getByRole("alert")).toHaveTextContent(
      /outside when the whole party is free/,
    );
    expect(screen.getByLabelText("Start date")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: "SAVE AND SEARCH FLIGHTS" })).toBeDisabled();
  });

  it("saves the new dates, starts a fresh flight search and closes", async () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: "One day shorter" }));
    fireEvent.change(screen.getByLabelText("Start date"), {
      target: { value: "2099-03-20" },
    });
    fireEvent.click(screen.getByRole("button", { name: "SAVE AND SEARCH FLIGHTS" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(changeDates).toHaveBeenCalledWith("room-1", {
      memberId: "m1",
      days: 5,
      start: "2099-03-20",
    });
    expect(startRun).toHaveBeenCalledWith("room-1", "m1", "logistics");
  });

  it("keeps the dialog open with the server's reason when the save is refused", async () => {
    changeDates.mockRejectedValue(
      new ApiError("TRIP_DATES_LOCKED", "The guide is searching flights right now.", 409),
    );
    open();
    fireEvent.click(screen.getByRole("button", { name: "One day longer" }));
    fireEvent.click(screen.getByRole("button", { name: "SAVE AND SEARCH FLIGHTS" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The guide is searching flights right now.",
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(startRun).not.toHaveBeenCalled();
  });
});
