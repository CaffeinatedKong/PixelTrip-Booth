/**
 * Destination service — real (backend-backed) implementation (DISCOVER stage).
 *
 * Follows the Supabase access boundary: the write (start run, cast vote) goes
 * through FastAPI; the reads of `messages` and `vote_sessions` are anon-key reads
 * of tables the party already watches, with Realtime subscriptions for live
 * updates. Failures surface as `ApiError`.
 */
import { getApiClient } from "@/lib/apiClient";
import { getSupabaseClient } from "@/lib/supabaseClient";
import { ApiError } from "@/lib/errors";
import type { Unsubscribe } from "@/types";

import type {
  BreakTieInput,
  CastDestinationVoteInput,
  DestinationOption,
  DestinationService,
  DestinationVote,
  DiscoverState,
  SelectedDestination,
  StartDiscoveryInput,
  TiebreakAdvice,
  TiebreakOption,
} from "./destination.contract";

interface MessageRow {
  id: string;
  kind: string;
  content: Record<string, unknown>;
  created_at: string;
}

interface VoteSessionRow {
  id: string;
  question: string;
  options: { id: string; label: string }[];
  status: "open" | "closed";
  tie_pending: boolean | null;
  tie_option_ids: string[] | null;
  category: "destination" | "flight" | null;
}

interface VoteRow {
  option_id: string;
}

interface SelectionRow {
  data: Record<string, unknown>;
}

function readError(table: string): ApiError {
  return new ApiError("DATABASE_ERROR", `Could not read ${table}.`, null);
}

/** Pull destination options out of a recommendation message's content. */
function toOptions(content: Record<string, unknown>): DestinationOption[] {
  const items = content.items;
  if (!Array.isArray(items)) return [];
  return items.map((raw) => {
    const item = raw as Record<string, unknown>;
    return {
      id: String(item.id ?? ""),
      title: String(item.title ?? ""),
      description:
        typeof item.description === "string" ? item.description : undefined,
      meta:
        item.meta && typeof item.meta === "object"
          ? (item.meta as Record<string, unknown>)
          : undefined,
    };
  });
}

/** Parse a `*_tiebreak` summary message's content into TiebreakAdvice. */
function toTiebreakAdvice(
  content: Record<string, unknown>,
  voteSessionId: string,
): TiebreakAdvice | null {
  const category = String(content.category ?? "");
  const base = category.endsWith("_tiebreak")
    ? (category.replace("_tiebreak", "") as "destination" | "flight")
    : null;
  if (base !== "destination" && base !== "flight") return null;

  const rawItems = Array.isArray(content.items) ? content.items : [];
  const options: TiebreakOption[] = rawItems.map((raw) => {
    const item = raw as Record<string, unknown>;
    const num = (v: unknown): number | undefined =>
      typeof v === "number" && Number.isFinite(v) ? v : undefined;
    const str = (v: unknown): string | undefined =>
      typeof v === "string" && v.trim() !== "" ? v : undefined;
    const memberFit = Array.isArray(item.memberFit)
      ? item.memberFit.map((f) => {
          const fit = f as Record<string, unknown>;
          return {
            memberId: String(fit.memberId ?? ""),
            displayName: String(fit.displayName ?? ""),
            score: num(fit.score) ?? 0,
            reason: String(fit.reason ?? ""),
          };
        })
      : undefined;
    return {
      id: String(item.id ?? ""),
      title: String(item.title ?? item.label ?? ""),
      description: str(item.description),
      score: num(item.score),
      whyThisFits: str(item.whyThisFits),
      tags: Array.isArray(item.tags) ? item.tags.map(String) : undefined,
      tradeOff: str(item.tradeOff),
      details: str(item.details),
      votes: Array.isArray(item.votes) ? item.votes.map(String) : undefined,
      memberFit,
    };
  });

  // SummaryMessageContent stores top-level fields snake_case (no camel alias);
  // the hand-built items[] use camelCase. Read the snake_case key here.
  const recommended = content.recommended_option_id;
  return {
    voteSessionId,
    category: base,
    advice: String(content.advice ?? content.text ?? ""),
    recommendedOptionId:
      typeof recommended === "string" && recommended.trim() !== ""
        ? recommended
        : null,
    options,
  };
}

class DestinationApiService implements DestinationService {
  async getTripId(roomId: string): Promise<string | null> {
    const { data, error } = await getSupabaseClient()
      .from("trips")
      .select("id")
      .eq("room_id", roomId)
      .maybeSingle<{ id: string }>();
    if (error) throw readError("trips");
    return data?.id ?? null;
  }

  async startDiscovery(input: StartDiscoveryInput): Promise<void> {
    await getApiClient().post(`/trips/${input.tripId}/runs`, {
      runType: "discovery",
      memberId: input.memberId,
      // Stable key so repeated clicks reuse the same run instead of starting new ones.
      idempotencyKey: `discovery-${input.tripId}`,
    });
  }

  async castVote(input: CastDestinationVoteInput): Promise<void> {
    await getApiClient().post(`/votes/${input.voteSessionId}/cast`, {
      memberId: input.memberId,
      optionId: input.optionId,
    });
  }

  async breakTie(input: BreakTieInput): Promise<void> {
    await getApiClient().post(`/votes/${input.voteSessionId}/break-tie`, {
      memberId: input.memberId,
      optionId: input.optionId,
    });
  }

  // --- live DISCOVER state ------------------------------------------------

  private async readState(roomId: string): Promise<DiscoverState> {
    const supabase = getSupabaseClient();

    // Latest destination recommendation message.
    const { data: messages, error: msgErr } = await supabase
      .from("messages")
      .select("id,kind,content,created_at")
      .eq("room_id", roomId)
      .eq("kind", "recommendation")
      .order("created_at", { ascending: false })
      .returns<MessageRow[]>();
    if (msgErr) throw readError("messages");

    const recommendation = (messages ?? []).find(
      (m) => (m.content as { category?: string }).category === "destination",
    );
    const options = recommendation ? toOptions(recommendation.content) : [];

    const { data: selection, error: selectionErr } = await supabase
      .from("selections")
      .select("data")
      .eq("room_id", roomId)
      .eq("kind", "destination")
      .maybeSingle<SelectionRow>();
    if (selectionErr) throw readError("selections");

    const selectionData = selection?.data ?? {};
    const selectedId = selectionData.id ?? selectionData.option_id;
    const selectedTitle = selectionData.title ?? selectionData.label;
    const selectedDestination: SelectedDestination | null =
      typeof selectedId === "string" && typeof selectedTitle === "string"
        ? { id: selectedId, title: selectedTitle }
        : null;

    // Open (or most recent) destination vote session.
    const { data: sessions, error: vsErr } = await supabase
      .from("vote_sessions")
      .select("id,question,options,status,tie_pending,tie_option_ids,category,message_id")
      .eq("room_id", roomId)
      .order("created_at", { ascending: false })
      .returns<VoteSessionRow[]>();
    if (vsErr) throw readError("vote_sessions");

    const sessionRow = (sessions ?? [])[0] ?? null;

    let vote: DestinationVote | null = null;
    if (sessionRow) {
      // Live per-option counts from the votes table.
      const { data: votes, error: vErr } = await supabase
        .from("votes")
        .select("option_id")
        .eq("vote_session_id", sessionRow.id)
        .returns<VoteRow[]>();
      if (vErr) throw readError("votes");
      const counts = new Map<string, number>();
      for (const v of votes ?? []) {
        counts.set(v.option_id, (counts.get(v.option_id) ?? 0) + 1);
      }
      vote = {
        voteSessionId: sessionRow.id,
        question: sessionRow.question,
        status: sessionRow.status,
        options: sessionRow.options.map((o) => ({
          id: o.id,
          label: o.label,
          count: counts.get(o.id) ?? 0,
        })),
      };
    }

    const tiePending = sessionRow?.tie_pending === true;

    let tiebreak: TiebreakAdvice | null = null;
    if (tiePending && sessionRow) {
      // Find the latest tiebreak advice summary message for this session's category.
      const { data: adviceMessages, error: aErr } = await supabase
        .from("messages")
        .select("id,kind,content,created_at")
        .eq("room_id", roomId)
        .eq("kind", "summary")
        .order("created_at", { ascending: false })
        .returns<MessageRow[]>();
      if (aErr) throw readError("messages");
      const wanted = `${sessionRow.category ?? "destination"}_tiebreak`;
      const adviceMsg = (adviceMessages ?? []).find(
        (m) => (m.content as { category?: string }).category === wanted,
      );
      if (adviceMsg) {
        tiebreak = toTiebreakAdvice(adviceMsg.content, sessionRow.id);
      }
    }

    return {
      loading: options.length === 0 && vote === null,
      options,
      selectedDestination,
      vote,
      tiePending,
      tiebreak,
    };
  }

  subscribeDiscover(
    roomId: string,
    onChange: (state: DiscoverState) => void,
  ): Unsubscribe {
    const supabase = getSupabaseClient();

    const push = async (): Promise<void> => {
      try {
        onChange(await this.readState(roomId));
      } catch {
        // Keep the last known state; never throw into the UI.
      }
    };

    void push();

    // Any change to the room's messages, vote sessions, or votes re-reads state.
    const channel = supabase
      .channel(`discover:${roomId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "messages", filter: `room_id=eq.${roomId}` },
        () => void push(),
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "vote_sessions", filter: `room_id=eq.${roomId}` },
        () => void push(),
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "votes" },
        () => void push(),
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "selections", filter: `room_id=eq.${roomId}` },
        () => void push(),
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }
}

export const destinationApiService: DestinationService =
  new DestinationApiService();
