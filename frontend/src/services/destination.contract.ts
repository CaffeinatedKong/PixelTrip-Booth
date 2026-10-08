/**
 * Destination service contract (DISCOVER stage).
 *
 * The AI produces destination recommendations and opens a vote: a `discovery` run
 * (`POST /trips/{tripId}/runs`) posts a `kind:"recommendation"` message
 * (`category:"destination"`) and opens a `vote_sessions` row. Members cast votes
 * (`POST /votes/{voteSessionId}/cast`); when the last votes, the session resolves
 * and the trip advances to `destination_selected`.
 *
 * This service exposes exactly what the DISCOVER screen needs. Shapes mirror the
 * "Recommendation Response Structure" and "Voting Structure" in `api-contracts.md`.
 * No Supabase/FastAPI types appear here.
 */
import type { Unsubscribe } from "@/types";

/** One recommended destination option the party can vote for. */
export interface DestinationOption {
  id: string;
  title: string;
  description?: string;
  /** Comparison details (region, budget band, highlights, ...). */
  meta?: Record<string, unknown>;
}

/** The open (or resolved) destination vote. */
export interface DestinationVote {
  voteSessionId: string;
  question: string;
  options: readonly { id: string; label: string; count: number }[];
  status: "open" | "closed";
}

/** A snapshot of the DISCOVER stage for a room. */
export interface DiscoverState {
  /** True while a discovery run is in progress and nothing is posted yet. */
  loading: boolean;
  /** The recommended destinations, or empty until the AI posts them. */
  options: readonly DestinationOption[];
  /** The destination vote, or null until the AI opens it. */
  vote: DestinationVote | null;
}

export interface StartDiscoveryInput {
  tripId: string;
  memberId: string;
}

export interface CastDestinationVoteInput {
  voteSessionId: string;
  memberId: string;
  optionId: string;
}

export interface DestinationService {
  /**
   * Resolve the trip id for a room (needed to start runs / read trip status).
   */
  getTripId(roomId: string): Promise<string | null>;

  /**
   * Ensure a discovery run is running for the trip. Idempotent on the backend
   * (an in-progress run of the same type is returned), so this is safe to call
   * from any member — though the UI only triggers it from the owner.
   */
  startDiscovery(input: StartDiscoveryInput): Promise<void>;

  /**
   * Live DISCOVER state for a room: the AI's recommendation options and the vote.
   * Primes once immediately, then updates on every `messages` / `vote_sessions`
   * change via Supabase Realtime. Returns an {@link Unsubscribe}.
   */
  subscribeDiscover(
    roomId: string,
    onChange: (state: DiscoverState) => void,
  ): Unsubscribe;

  /** Cast (or change) this member's destination vote. */
  castVote(input: CastDestinationVoteInput): Promise<void>;
}
