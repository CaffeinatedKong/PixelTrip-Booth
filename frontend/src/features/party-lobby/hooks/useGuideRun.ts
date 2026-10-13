"use client";

/**
 * useGuideRun — the latest AI run of a type for the room, while `active`.
 *
 * Reads through the shared poller (see `lib/runPoller.ts`), so several hooks on one
 * screen cost one request stream, which speeds up while a run is going and slows once it
 * has finished. `refresh` re-reads at once (e.g. after a retry).
 *
 * A failed read keeps the last run (shown only if one was ever read) and sets `error`
 * until the next read succeeds, so the screen can say the status is unavailable instead
 * of looking like "the guide has not started".
 */
import { useCallback, useEffect, useRef, useState } from "react";

import type { RunProgress, RunType } from "@/services/run.contract";

import { subscribeRun, type RunSubscription } from "../lib/runPoller";

export interface GuideRun {
  run: RunProgress | null;
  /** True once the first read has answered, so `run: null` means "no run yet". */
  loaded: boolean;
  /** Set while the latest status read is failing; cleared by the next good read. */
  error: string | null;
  refresh: () => void;
}

export function useGuideRun(
  roomId: string,
  runType: RunType,
  active: boolean,
): GuideRun {
  const [run, setRun] = useState<RunProgress | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const subscription = useRef<RunSubscription | null>(null);

  useEffect(() => {
    if (!active) return;
    const handle = subscribeRun(roomId, runType, (update) => {
      if (update.loaded) {
        setRun(update.run);
        setLoaded(true);
      }
      setError(update.error ? "Could not check on the guide. Retrying…" : null);
    });
    subscription.current = handle;
    return () => {
      handle.unsubscribe();
      subscription.current = null;
    };
  }, [roomId, runType, active]);

  const refresh = useCallback(() => subscription.current?.refresh(), []);

  return { run, loaded, error, refresh };
}
