/**
 * runPoller: one shared poll per (room, run type), adaptive, with backoff.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  IDLE_MS,
  LIVE_ACTIVE_MS,
  LIVE_IDLE_MS,
  MAX_BACKOFF_MS,
  resetRunPollers,
  subscribeRun,
} from "./runPoller";

const getLatestRun = vi.fn();

// The push channel, driven by hand: `channel` holds the callbacks of the latest subscribe.
const stopChannel = vi.fn();
const channel: {
  push?: (run: unknown) => void;
  live?: (live: boolean) => void;
  subscribed: string[];
} = { subscribed: [] };
const subscribeProgress = vi.fn(
  (
    roomId: string,
    onProgress: (run: unknown) => void,
    onLive: (live: boolean) => void,
  ) => {
    channel.subscribed.push(roomId);
    channel.push = onProgress;
    channel.live = onLive;
    return stopChannel;
  },
);

vi.mock("@/services", () => ({
  getServices: () => ({ run: { getLatestRun, subscribeProgress } }),
}));

const running = { id: "r", status: "running", phase: "asking_guide" };
const done = { id: "r", status: "completed", phase: null };

beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(Math, "random").mockReturnValue(0.5); // no jitter
  getLatestRun.mockReset();
  subscribeProgress.mockClear();
  stopChannel.mockReset();
  channel.subscribed = [];
  channel.push = undefined;
  channel.live = undefined;
});

afterEach(() => {
  resetRunPollers();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("subscribeRun", () => {
  it("shares one request stream between many subscribers", async () => {
    getLatestRun.mockResolvedValue(running);
    const updates = [vi.fn(), vi.fn(), vi.fn()];

    updates.forEach((fn) => subscribeRun("room", "discovery", fn));
    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(2000);
    await vi.advanceTimersByTimeAsync(2000);

    expect(getLatestRun).toHaveBeenCalledTimes(3); // not 9
    for (const fn of updates) {
      expect(fn).toHaveBeenLastCalledWith({
        run: running,
        loaded: true,
        error: false,
      });
    }
  });

  it("keeps separate polls for different rooms and run types", async () => {
    getLatestRun.mockResolvedValue(running);

    subscribeRun("room-a", "discovery", vi.fn());
    subscribeRun("room-a", undefined, vi.fn());
    subscribeRun("room-b", "discovery", vi.fn());
    await vi.advanceTimersByTimeAsync(0);

    expect(getLatestRun).toHaveBeenCalledTimes(3);
  });

  it("replays what is known to a late subscriber without another request", async () => {
    getLatestRun.mockResolvedValue(running);
    subscribeRun("room", "discovery", vi.fn());
    await vi.advanceTimersByTimeAsync(0);

    const late = vi.fn();
    subscribeRun("room", "discovery", late);

    expect(late).toHaveBeenCalledWith({
      run: running,
      loaded: true,
      error: false,
    });
    expect(getLatestRun).toHaveBeenCalledTimes(1);
  });

  it("slows down once the run has finished", async () => {
    getLatestRun.mockResolvedValue(done);
    subscribeRun("room", "discovery", vi.fn());
    await vi.advanceTimersByTimeAsync(0);

    await vi.advanceTimersByTimeAsync(IDLE_MS - 1);
    expect(getLatestRun).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(getLatestRun).toHaveBeenCalledTimes(2);
  });

  it("backs off while failing, reports the error, and recovers", async () => {
    getLatestRun.mockRejectedValue(new Error("down"));
    const listener = vi.fn();
    subscribeRun("room", "discovery", listener);
    await vi.advanceTimersByTimeAsync(0);
    expect(listener).toHaveBeenLastCalledWith({
      run: null,
      loaded: false,
      error: true,
    });

    await vi.advanceTimersByTimeAsync(IDLE_MS); // 1st retry after 6s
    await vi.advanceTimersByTimeAsync(IDLE_MS * 2); // then 12s
    expect(getLatestRun).toHaveBeenCalledTimes(3);

    getLatestRun.mockResolvedValue(running);
    await vi.advanceTimersByTimeAsync(MAX_BACKOFF_MS);
    expect(listener).toHaveBeenLastCalledWith({
      run: running,
      loaded: true,
      error: false,
    });
  });

  it("stops polling when the last subscriber leaves", async () => {
    getLatestRun.mockResolvedValue(running);
    const sub = subscribeRun("room", "discovery", vi.fn());
    await vi.advanceTimersByTimeAsync(0);

    sub.unsubscribe();
    await vi.advanceTimersByTimeAsync(60000);

    expect(getLatestRun).toHaveBeenCalledTimes(1);
  });

  it("refresh reads immediately", async () => {
    getLatestRun.mockResolvedValue(done);
    const sub = subscribeRun("room", "discovery", vi.fn());
    await vi.advanceTimersByTimeAsync(0);

    sub.refresh();
    await vi.advanceTimersByTimeAsync(0);

    expect(getLatestRun).toHaveBeenCalledTimes(2);
  });
});

describe("pushed progress", () => {
  const push = (over: Record<string, unknown> = {}) => ({
    id: "r",
    runType: "discovery",
    status: "running",
    phase: "asking_guide",
    elapsedSeconds: 3,
    ...over,
  });

  it("joins one channel per room, however many hooks follow it", () => {
    subscribeRun("room", "discovery", vi.fn());
    subscribeRun("room", undefined, vi.fn());
    subscribeRun("room", "logistics", vi.fn());
    subscribeRun("other", "discovery", vi.fn());

    expect(channel.subscribed).toEqual(["room", "other"]);
  });

  it("closes the channel when the last follower of the room leaves", () => {
    const a = subscribeRun("room", "discovery", vi.fn());
    const b = subscribeRun("room", undefined, vi.fn());

    a.unsubscribe();
    expect(stopChannel).not.toHaveBeenCalled();
    b.unsubscribe();
    expect(stopChannel).toHaveBeenCalledTimes(1);
  });

  it("shows a pushed step at once, without another request", async () => {
    getLatestRun.mockResolvedValue(null);
    const listener = vi.fn();
    subscribeRun("room", "discovery", listener);
    await vi.advanceTimersByTimeAsync(0);
    getLatestRun.mockClear();

    channel.push?.(push({ phase: "checking_budget" }));

    expect(listener).toHaveBeenLastCalledWith({
      run: expect.objectContaining({ phase: "checking_budget" }),
      loaded: true,
      error: false,
    });
    expect(getLatestRun).not.toHaveBeenCalled();
  });

  it("applies a push to a typed follower only for its own run type", async () => {
    getLatestRun.mockResolvedValue(null);
    const discovery = vi.fn();
    const logistics = vi.fn();
    const any = vi.fn();
    subscribeRun("room", "discovery", discovery);
    subscribeRun("room", "logistics", logistics);
    subscribeRun("room", undefined, any);
    await vi.advanceTimersByTimeAsync(0);
    for (const fn of [discovery, logistics, any]) fn.mockClear();

    channel.push?.(push({ runType: "logistics", phase: "searching_flights" }));

    expect(logistics).toHaveBeenCalledTimes(1);
    expect(any).toHaveBeenCalledTimes(1);
    expect(discovery).not.toHaveBeenCalled();
  });

  it("ignores an earlier state of a run that arrives after a later one", async () => {
    getLatestRun.mockResolvedValue(null);
    const listener = vi.fn();
    subscribeRun("room", "discovery", listener);
    await vi.advanceTimersByTimeAsync(0);

    channel.push?.(push({ status: "completed", phase: "posting" }));
    channel.push?.(push({ status: "running", phase: "checking_answer" })); // late arrival

    expect(listener).toHaveBeenLastCalledWith(
      expect.objectContaining({
        run: expect.objectContaining({ status: "completed" }),
      }),
    );
  });

  it("confirms with one read shortly after a run ends", async () => {
    getLatestRun.mockResolvedValue(null);
    subscribeRun("room", "discovery", vi.fn());
    await vi.advanceTimersByTimeAsync(0);
    getLatestRun.mockClear();

    channel.push?.(push({ status: "completed", phase: "posting" }));
    await vi.advanceTimersByTimeAsync(1000);

    expect(getLatestRun).toHaveBeenCalledTimes(1);
  });

  it("polls only as a slow backstop while the channel is live", async () => {
    getLatestRun.mockResolvedValue(running);
    subscribeRun("room", "discovery", vi.fn());
    channel.live?.(true);
    await vi.advanceTimersByTimeAsync(0);
    getLatestRun.mockClear();

    await vi.advanceTimersByTimeAsync(LIVE_ACTIVE_MS - 1);
    expect(getLatestRun).not.toHaveBeenCalled(); // not at the old 2s pace
    await vi.advanceTimersByTimeAsync(1);
    expect(getLatestRun).toHaveBeenCalledTimes(1);
  });

  it("backs off further when nothing is running and the channel is live", async () => {
    getLatestRun.mockResolvedValue(done);
    subscribeRun("room", "discovery", vi.fn());
    channel.live?.(true);
    await vi.advanceTimersByTimeAsync(0);
    getLatestRun.mockClear();

    await vi.advanceTimersByTimeAsync(LIVE_IDLE_MS - 1);
    expect(getLatestRun).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(getLatestRun).toHaveBeenCalledTimes(1);
  });

  it("goes back to the normal pace when the channel drops", async () => {
    getLatestRun.mockResolvedValue(running);
    subscribeRun("room", "discovery", vi.fn());
    channel.live?.(true);
    await vi.advanceTimersByTimeAsync(0);
    channel.live?.(false);
    getLatestRun.mockClear();

    await vi.advanceTimersByTimeAsync(10000);

    expect(getLatestRun.mock.calls.length).toBeGreaterThanOrEqual(4); // ~every 2s
  });

  it("reads once when the channel connects, to catch up on anything missed", async () => {
    getLatestRun.mockResolvedValue(running);
    subscribeRun("room", "discovery", vi.fn());
    await vi.advanceTimersByTimeAsync(0);
    getLatestRun.mockClear();

    channel.live?.(true);
    await vi.advanceTimersByTimeAsync(0);

    expect(getLatestRun).toHaveBeenCalledTimes(1);
  });

  it("still polls normally when push is unavailable", async () => {
    subscribeProgress.mockImplementationOnce(() => {
      throw new Error("realtime not configured");
    });
    getLatestRun.mockResolvedValue(running);
    const listener = vi.fn();

    subscribeRun("room", "discovery", listener);
    await vi.advanceTimersByTimeAsync(2100);

    expect(listener).toHaveBeenLastCalledWith({
      run: running,
      loaded: true,
      error: false,
    });
    expect(getLatestRun).toHaveBeenCalledTimes(2);
  });
});
