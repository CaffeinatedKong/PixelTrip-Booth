/**
 * Run progress contract — what the AI guide is doing right now.
 *
 * Mirrors `GET /trips/{tripId}/runs/latest?runType=…`. `phase` is the real step
 * the run is on (or failed on); the UI maps it to an in-world line.
 */
import type { Unsubscribe } from "@/types";

export type RunType =
  | "discovery"
  | "logistics"
  | "itinerary"
  | "refinement"
  | "tiebreak";

export type RunPhase =
  | "reading_party"
  | "asking_guide"
  | "searching_flights"
  | "checking_budget"
  | "checking_answer"
  | "drafting_days"
  | "weighing_feedback"
  | "weighing_options"
  | "posting";

export interface RunProgress {
  id: string;
  runType: RunType;
  status: "pending" | "running" | "completed" | "failed";
  phase: RunPhase | null;
  elapsedSeconds: number;
}

export interface RunService {
  /** The room's latest run of a type (any type when omitted), or null before any run. */
  getLatestRun(roomId: string, runType?: RunType): Promise<RunProgress | null>;

  /**
   * Hear about run progress the moment it changes (Supabase Realtime Broadcast on
   * `run:<roomId>`), instead of asking again and again. `onLive(true)` once the channel is
   * connected, `onLive(false)` when it drops, so callers can fall back to polling. The
   * payload is `GET .../runs/latest`'s shape and carries no party data.
   */
  subscribeProgress(
    roomId: string,
    onProgress: (run: RunProgress) => void,
    onLive: (live: boolean) => void,
  ): Unsubscribe;

  /** Start a fresh run of a type (e.g. retry the tiebreak advice). */
  startRun(roomId: string, memberId: string, runType: RunType): Promise<void>;
}
