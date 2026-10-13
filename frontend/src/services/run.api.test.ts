/**
 * parseProgress: only a well-formed broadcast payload becomes run progress.
 */
import { describe, expect, it } from "vitest";

import { parseProgress } from "./run.api";

describe("parseProgress", () => {
  it("reads a well-formed payload", () => {
    expect(
      parseProgress({
        id: "r1",
        runType: "logistics",
        status: "running",
        phase: "searching_flights",
        elapsedSeconds: 7,
      }),
    ).toEqual({
      id: "r1",
      runType: "logistics",
      status: "running",
      phase: "searching_flights",
      elapsedSeconds: 7,
    });
  });

  it("treats a missing phase or elapsed time as null / 0", () => {
    expect(
      parseProgress({ id: "r", runType: "discovery", status: "pending" }),
    ).toEqual({
      id: "r",
      runType: "discovery",
      status: "pending",
      phase: null,
      elapsedSeconds: 0,
    });
  });

  it.each([
    null,
    "text",
    {},
    { id: "r", runType: "other", status: "running" },
    { id: "r", runType: "discovery", status: "paused" },
    { runType: "discovery", status: "running" },
  ])("rejects %j", (payload) => {
    expect(parseProgress(payload)).toBeNull();
  });
});
