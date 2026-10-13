"use client";

/**
 * useActiveGuideRun — the room's AI run while it is in progress, of any type.
 *
 * Returns the latest run while it is pending or running, otherwise null. Lets every
 * screen show that MILO is working, whoever started it. Shares one poll with every
 * other run hook on the screen (see `lib/runPoller.ts`).
 */
import { useEffect, useState } from "react";

import type { RunProgress } from "@/services/run.contract";

import { subscribeRun } from "../lib/runPoller";

export function useActiveGuideRun(roomId: string): RunProgress | null {
  const [run, setRun] = useState<RunProgress | null>(null);

  useEffect(() => {
    const handle = subscribeRun(roomId, undefined, (update) => {
      if (!update.loaded) return; // keep what we had if the very first read failed
      const latest = update.run;
      const active =
        latest?.status === "pending" || latest?.status === "running";
      setRun(active ? latest : null);
    });
    return handle.unsubscribe;
  }, [roomId]);

  return run;
}
