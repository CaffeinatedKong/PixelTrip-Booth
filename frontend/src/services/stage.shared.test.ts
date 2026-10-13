/**
 * Tests for the pure parts of the stage reader: tiebreak advice must belong to the
 * vote session being shown, not merely to the same category.
 */
import { describe, expect, it } from "vitest";

import { findTiebreakAdvice } from "./stage.shared";

const summary = (sessionId: string | undefined, advice: string) => ({
  kind: "summary" as const,
  content: {
    category: "flight_tiebreak",
    advice,
    recommended_option_id: "f1",
    items: [{ id: "f1", title: "Scoot" }],
    ...(sessionId ? { vote_session_id: sessionId } : {}),
  },
});

describe("findTiebreakAdvice", () => {
  it("returns the advice written for this vote session", () => {
    const advice = findTiebreakAdvice(
      [summary("session-2", "Take Scoot.")],
      "flight",
      "session-2",
    );

    expect(advice?.voteSessionId).toBe("session-2");
    expect(advice?.advice).toBe("Take Scoot.");
  });

  it("ignores advice from an earlier tie of the same category", () => {
    // Newest first: the earlier round's advice must not be shown for the new session.
    const advice = findTiebreakAdvice(
      [summary("session-1", "Old advice.")],
      "flight",
      "session-2",
    );

    expect(advice).toBeNull();
  });

  it("picks the right session's advice when several rounds exist", () => {
    const advice = findTiebreakAdvice(
      [summary("session-2", "New."), summary("session-1", "Old.")],
      "flight",
      "session-1",
    );

    expect(advice?.advice).toBe("Old.");
  });

  it("does not guess when the summary carries no session id", () => {
    expect(
      findTiebreakAdvice(
        [summary(undefined, "Unscoped.")],
        "flight",
        "session-1",
      ),
    ).toBeNull();
  });

  it("ignores other categories", () => {
    expect(
      findTiebreakAdvice(
        [summary("session-1", "Flights.")],
        "destination",
        "session-1",
      ),
    ).toBeNull();
  });
});
