"use client";

/**
 * DestinationStageContent — DISCOVER as a chatbot-style flow (left column only;
 * the shell owns the persistent sidebar).
 *
 * MILO (the NPC guide) frames the stage in chat bubbles, then presents the AI's
 * destination matches as rich cards (fit score, why-it-fits, tags, trade-off).
 * The owner's entry starts the discovery run; recommendations + the vote arrive
 * live via Supabase Realtime through the destination service. Members pick one
 * and submit a vote; after voting they see the waiting panel.
 */
import { useEffect, useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import { getServices } from "@/services";
import { ApiError } from "@/lib/errors";
import type { DiscoverState } from "@/services/destination.contract";
import type { RoomMember, RoomSession } from "@/types";

import { WaitingForParty } from "./WaitingForParty";
import { DestinationMatchCard } from "./DestinationMatchCard";
import { StageChat, GuideSay, GuideMessage } from "./StageChat";
import { TiebreakPanel } from "./TiebreakPanel";

export interface DestinationStageContentProps {
  session: RoomSession;
  members: RoomMember[];
}

export function DestinationStageContent({
  session,
  members,
}: DestinationStageContentProps): ReactElement {
  const isOwner = session.member.role === "owner";
  const roomId = session.room.id;
  const memberId = session.member.id;

  const [discover, setDiscover] = useState<DiscoverState>({
    loading: true,
    options: [],
    vote: null,
    tiePending: false,
    tiebreak: null,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [voting, setVoting] = useState(false);
  const [voted, setVoted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Owner's tie-break submission state.
  const [deciding, setDeciding] = useState(false);
  const [tieError, setTieError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const service = getServices().destination;

    const kickOff = async (): Promise<void> => {
      if (!isOwner) return;
      try {
        const tripId = await service.getTripId(roomId);
        if (tripId && !cancelled) {
          await service.startDiscovery({ tripId, memberId });
        }
      } catch {
        // Subscription still surfaces whatever the AI posts.
      }
    };
    void kickOff();

    const unsubscribe = service.subscribeDiscover(roomId, (state) => {
      if (!cancelled) setDiscover(state);
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [roomId, memberId, isOwner]);

  const vote = discover.vote;
  const viewer = members.find((m) => m.id === memberId);
  const viewerReady = voted || viewer?.stageReady === true;

  const handleVote = async (): Promise<void> => {
    if (!vote || selectedId === null || voting) return;
    setVoting(true);
    setError(null);
    try {
      await getServices().destination.castVote({
        voteSessionId: vote.voteSessionId,
        memberId,
        optionId: selectedId,
      });
      setVoted(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not cast your vote. Please try again.",
      );
    } finally {
      setVoting(false);
    }
  };

  const handleBreakTie = async (optionId: string): Promise<void> => {
    if (!discover.tiebreak || deciding) return;
    setDeciding(true);
    setTieError(null);
    try {
      await getServices().destination.breakTie({
        voteSessionId: discover.tiebreak.voteSessionId,
        memberId,
        optionId,
      });
    } catch (err) {
      setTieError(
        err instanceof ApiError
          ? err.message
          : "Could not lock in the choice. Please try again.",
      );
    } finally {
      setDeciding(false);
    }
  };

  // Prefer rich recommendation items (carry description/meta); fall back to the
  // vote options (id + label only) if the recommendation message is not in yet.
  const matches =
    discover.options.length > 0
      ? discover.options.map((o) => ({
          id: o.id,
          title: o.title,
          description: o.description,
          meta: o.meta,
        }))
      : (vote?.options ?? []).map((o) => ({ id: o.id, title: o.label }));

  const hasMatches = matches.length > 0;

  return (
    <StageChat>
      <GuideSay text="The party is formed! Let's find where your journey begins." />
      <GuideSay text="Putting your group's preferences together — this takes a moment." />

      {discover.tiePending && discover.tiebreak ? (
        <GuideMessage>
          <TiebreakPanel
            tiebreak={discover.tiebreak}
            isOwner={isOwner}
            deciding={deciding}
            error={tieError}
            onBreakTie={(optionId) => {
              void handleBreakTie(optionId);
            }}
          />
        </GuideMessage>
      ) : viewerReady ? (
        <GuideMessage>
          <WaitingForParty members={members} what="destination vote" />
        </GuideMessage>
      ) : (
        <GuideMessage>
          <div className="flex flex-col gap-16">
            <p className="font-body">
              Here are your best destination matches. Pick the one that excites
              you most, then lock in your vote.
            </p>

            {!hasMatches ? (
              <div className="border-2 border-dashed border-muted p-16">
                <p className="font-body text-muted">
                  No destinations generated yet
                  {discover.loading ? " — the guide is still thinking…" : "."}
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-16">
                {matches.map((option) => (
                  <DestinationMatchCard
                    key={option.id}
                    option={option}
                    selected={selectedId === option.id}
                    onToggle={(id) =>
                      setSelectedId((prev) => (prev === id ? null : id))
                    }
                  />
                ))}
              </div>
            )}

            {error !== null ? (
              <p role="alert" className="font-body text-danger">
                {error}
              </p>
            ) : null}

            {hasMatches ? (
              <PixelButton
                variant="primary"
                type="button"
                label={voting ? "CASTING…" : "LOCK IN VOTE"}
                disabled={selectedId === null || voting || vote === null}
                onClick={() => {
                  void handleVote();
                }}
              />
            ) : null}
          </div>
        </GuideMessage>
      )}
    </StageChat>
  );
}

export default DestinationStageContent;
