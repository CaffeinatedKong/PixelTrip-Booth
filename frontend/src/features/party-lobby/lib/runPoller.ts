/**
 * Following a room's AI run progress, cheaply.
 *
 * Several parts of one screen ask the same question ("how is the guide getting on?"):
 * the sidebar, the active stage, and BUILD/REFINE can mount a second run hook. Each used
 * to poll on its own, and every party member's browser does the same, so progress
 * animation alone produced tens of requests a second in a full room. Now:
 *
 * - **The backend pushes.** It broadcasts each step on the room's `run:<roomId>` channel,
 *   so a connected browser hears about a change at once instead of asking for it.
 * - **Polling is the backstop**, slow while the channel is live (10s during a run, 30s
 *   otherwise, to refresh the elapsed time and catch anything missed) and at the old pace
 *   (2s during a run, 6s otherwise) when it is not, with backoff while requests fail.
 * - **Everything in a tab shares one subscription and one poll** per (room, run type).
 * - **The tab pauses polling while hidden**, and the delays are jittered so a room that
 *   opened together does not poll in lockstep.
 *
 * The backend also answers the poll from a 2-second cache, so what polling remains costs
 * about one database read per trip per interval, not one per person.
 */
import { getServices } from "@/services";
import type { RunProgress, RunType } from "@/services/run.contract";

export interface RunPollUpdate {
  /** The latest run, kept from the last successful read when `error` is true. */
  run: RunProgress | null;
  /** True once at least one read (or push) has succeeded. */
  loaded: boolean;
  /** True while the most recent read is failing. */
  error: boolean;
}

type Listener = (update: RunPollUpdate) => void;

export const ACTIVE_MS = 2000;
export const IDLE_MS = 6000;
export const MAX_BACKOFF_MS = 30000;
/** Polling pace while the push channel is connected. */
export const LIVE_ACTIVE_MS = 10000;
export const LIVE_IDLE_MS = 30000;
/** After a run ends, confirm with one read soon (the push can race the final write). */
const CONFIRM_MS = 600;

interface Poller {
  roomId: string;
  runType: RunType | undefined;
  listeners: Set<Listener>;
  last: RunPollUpdate;
  failures: number;
  timer: ReturnType<typeof setTimeout> | undefined;
  inFlight: boolean;
}

interface RoomChannel {
  pollers: Set<Poller>;
  live: boolean;
  stop: () => void;
}

const pollers = new Map<string, Poller>();
const channels = new Map<string, RoomChannel>();

const jitter = (ms: number): number => ms * (0.9 + Math.random() * 0.2);

const isRunning = (run: RunProgress | null | undefined): boolean =>
  run?.status === "pending" || run?.status === "running";

const rank = (status: RunProgress["status"]): number =>
  status === "pending" ? 0 : status === "running" ? 1 : 2;

function nextDelay(poller: Poller): number {
  if (poller.failures > 0) {
    return Math.min(IDLE_MS * 2 ** (poller.failures - 1), MAX_BACKOFF_MS);
  }
  const live = channels.get(poller.roomId)?.live === true;
  if (isRunning(poller.last.run)) return live ? LIVE_ACTIVE_MS : ACTIVE_MS;
  return live ? LIVE_IDLE_MS : IDLE_MS;
}

function schedule(poller: Poller, delay: number): void {
  if (poller.timer) clearTimeout(poller.timer);
  poller.timer = setTimeout(() => void poll(poller), jitter(delay));
}

function emit(poller: Poller): void {
  for (const listener of [...poller.listeners]) listener(poller.last);
}

async function poll(poller: Poller): Promise<void> {
  if (poller.inFlight || poller.listeners.size === 0) return;
  if (typeof document !== "undefined" && document.hidden) {
    schedule(poller, IDLE_MS); // look again later; nothing is watching right now
    return;
  }
  poller.inFlight = true;
  try {
    const run = await getServices().run.getLatestRun(
      poller.roomId,
      poller.runType,
    );
    poller.failures = 0;
    poller.last = { run, loaded: true, error: false };
  } catch {
    poller.failures += 1;
    poller.last = { ...poller.last, error: true };
  } finally {
    poller.inFlight = false;
  }
  if (poller.listeners.size === 0) return;
  emit(poller);
  schedule(poller, nextDelay(poller));
}

/** A step pushed by the backend: apply it to the pollers it concerns. */
function applyPush(roomId: string, pushed: RunProgress): void {
  const channel = channels.get(roomId);
  if (!channel) return;
  for (const poller of channel.pollers) {
    if (poller.runType !== undefined && poller.runType !== pushed.runType)
      continue;
    const held = poller.last.run;
    // Pushes are sent without waiting for each other, so they can arrive out of order:
    // never let an earlier state of the same run replace a later one.
    if (
      held &&
      held.id === pushed.id &&
      rank(pushed.status) < rank(held.status)
    )
      continue;
    poller.last = { run: pushed, loaded: true, error: false };
    poller.failures = 0;
    emit(poller);
    if (isRunning(pushed)) schedule(poller, nextDelay(poller));
    else schedule(poller, CONFIRM_MS);
  }
}

function joinChannel(roomId: string, poller: Poller): void {
  let channel = channels.get(roomId);
  if (!channel) {
    const created: RoomChannel = {
      pollers: new Set(),
      live: false,
      stop: () => {},
    };
    channels.set(roomId, created);
    channel = created;
    try {
      created.stop = getServices().run.subscribeProgress(
        roomId,
        (pushed) => applyPush(roomId, pushed),
        (live) => {
          if (created.live === live) return;
          created.live = live;
          for (const p of created.pollers) {
            // Connected: read once now so nothing sent before we joined is missed.
            // Dropped: stop waiting out a slow backstop delay and resume the normal pace.
            schedule(p, live ? 0 : nextDelay(p));
          }
        },
      );
    } catch {
      created.live = false; // no push available (e.g. not configured); polling covers it
    }
  }
  channel.pollers.add(poller);
}

function leaveChannel(roomId: string, poller: Poller): void {
  const channel = channels.get(roomId);
  if (!channel) return;
  channel.pollers.delete(poller);
  if (channel.pollers.size === 0) {
    channel.stop();
    channels.delete(roomId);
  }
}

export interface RunSubscription {
  unsubscribe: () => void;
  /** Read now instead of waiting for the next tick (e.g. right after a retry). */
  refresh: () => void;
}

/** Follow a room's latest run. All callers asking for the same thing share one poll. */
export function subscribeRun(
  roomId: string,
  runType: RunType | undefined,
  listener: Listener,
): RunSubscription {
  const key = `${roomId}:${runType ?? "any"}`;
  let poller = pollers.get(key);
  if (!poller) {
    poller = {
      roomId,
      runType,
      listeners: new Set(),
      last: { run: null, loaded: false, error: false },
      failures: 0,
      timer: undefined,
      inFlight: false,
    };
    pollers.set(key, poller);
  }
  const shared = poller;
  const first = shared.listeners.size === 0;
  shared.listeners.add(listener);

  if (first) joinChannel(roomId, shared);

  if (shared.last.loaded || shared.last.error) {
    listener(shared.last); // a later subscriber starts from what is already known
  } else if (first) {
    void poll(shared);
  }

  return {
    unsubscribe: () => {
      shared.listeners.delete(listener);
      if (shared.listeners.size === 0) {
        if (shared.timer) clearTimeout(shared.timer);
        if (pollers.get(key) === shared) pollers.delete(key);
        leaveChannel(roomId, shared);
      }
    },
    refresh: () => {
      if (shared.timer) clearTimeout(shared.timer);
      void poll(shared);
    },
  };
}

/** Test hook: forget every poller and channel. */
export function resetRunPollers(): void {
  for (const poller of pollers.values()) {
    if (poller.timer) clearTimeout(poller.timer);
  }
  for (const channel of channels.values()) channel.stop();
  pollers.clear();
  channels.clear();
}
