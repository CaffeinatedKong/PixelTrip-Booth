/** Run progress — real implementation (`GET /trips/{tripId}/runs/latest`). */
import { getApiClient } from "@/lib/apiClient";
import { getSupabaseClient } from "@/lib/supabaseClient";

import type { RunProgress, RunService, RunType } from "./run.contract";

const RUN_TYPES = ["discovery", "logistics", "itinerary", "refinement", "tiebreak"];
const STATUSES = ["pending", "running", "completed", "failed"];

/** A broadcast payload as a RunProgress, or null if it is not one. */
export function parseProgress(payload: unknown): RunProgress | null {
  const p = payload as Partial<Record<string, unknown>> | null;
  if (!p || typeof p !== "object") return null;
  if (
    typeof p.id !== "string" ||
    typeof p.runType !== "string" ||
    !RUN_TYPES.includes(p.runType) ||
    typeof p.status !== "string" ||
    !STATUSES.includes(p.status)
  ) {
    return null;
  }
  return {
    id: p.id,
    runType: p.runType as RunProgress["runType"],
    status: p.status as RunProgress["status"],
    phase: typeof p.phase === "string" ? (p.phase as RunProgress["phase"]) : null,
    elapsedSeconds: typeof p.elapsedSeconds === "number" ? p.elapsedSeconds : 0,
  };
}

class RunApiService implements RunService {
  private tripIds = new Map<string, string>();

  private async tripId(roomId: string): Promise<string | null> {
    const cached = this.tripIds.get(roomId);
    if (cached) return cached;
    const { data, error } = await getSupabaseClient()
      .from("trips")
      .select("id")
      .eq("room_id", roomId)
      .maybeSingle<{ id: string }>();
    if (error || !data) return null;
    this.tripIds.set(roomId, data.id);
    return data.id;
  }

  async getLatestRun(roomId: string, runType?: RunType): Promise<RunProgress | null> {
    const tripId = await this.tripId(roomId);
    if (!tripId) return null;
    const query = runType ? `?runType=${runType}` : "";
    return getApiClient().get<RunProgress | null>(`/trips/${tripId}/runs/latest${query}`);
  }

  subscribeProgress(
    roomId: string,
    onProgress: (run: RunProgress) => void,
    onLive: (live: boolean) => void,
  ): () => void {
    const supabase = getSupabaseClient();
    const channel = supabase
      .channel(`run:${roomId}`)
      .on("broadcast", { event: "progress" }, ({ payload }) => {
        const run = parseProgress(payload);
        if (run) onProgress(run);
      })
      .subscribe((status) => onLive(status === "SUBSCRIBED"));
    return () => {
      void supabase.removeChannel(channel);
    };
  }

  async startRun(roomId: string, memberId: string, runType: RunType): Promise<void> {
    const tripId = await this.tripId(roomId);
    if (!tripId) {
      // Not "nothing to do": the caller would think a run started and wait for it.
      throw new Error("Could not find this trip to start the guide.");
    }
    // Always a fresh key: the backend returns the earlier run for a known key.
    await getApiClient().post(`/trips/${tripId}/runs`, {
      runType,
      memberId,
      idempotencyKey: `${runType}-${tripId}-retry-${Date.now()}`,
    });
  }
}

export const runApiService: RunService = new RunApiService();
