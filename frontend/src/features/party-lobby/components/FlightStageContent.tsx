"use client";

/**
 * FlightStageContent — LOGISTICS as a chatbot-style flow (left column only; the
 * shell owns the persistent sidebar). Mirrors DestinationStageContent.
 *
 * The owner's entry starts the logistics run (flight search for the locked
 * destination, filtered by dates and budget). While the guide works, the party
 * sees its real steps (GuideThinking) over placeholder cards; then the flights
 * arrive live as FlightMatchCards, members vote, and a tie goes to the owner via
 * the shared TiebreakPanel. A failed or empty run shows why, with a retry for
 * the owner.
 */
import { useEffect, useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import { ApiError } from "@/lib/errors";
import { getServices } from "@/services";
import type { LogisticsState } from "@/services/flight.contract";
import type { RoomMember, RoomSession } from "@/types";

import { useGuideRun } from "../hooks/useGuideRun";
import { FlightMatchCard } from "./FlightMatchCard";
import { GuideThinking } from "./GuideThinking";
import { SkeletonCards } from "./SkeletonCards";
import { GuideMessage, GuideSay, StageChat } from "./StageChat";
import { TiebreakPanel } from "./TiebreakPanel";
import { WaitingForParty } from "./WaitingForParty";

export interface FlightStageContentProps {
  session: RoomSession;
  members: RoomMember[];
}

const EMPTY: LogisticsState = {
  loading: true,
  options: [],
  selectedFlight: null,
  vote: null,
  tiePending: false,
  tiebreak: null,
  guideNote: null,
};

export function FlightStageContent({
  session,
  members,
}: FlightStageContentProps): ReactElement {
  const isOwner = session.member.role === "owner";
  const roomId = session.room.id;
  const memberId = session.member.id;

  const [state, setState] = useState<LogisticsState>(EMPTY);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [voting, setVoting] = useState(false);
  const [voted, setVoted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [tieError, setTieError] = useState<string | null>(null);

  const hasFlights = state.options.length > 0;
  const { run, refresh } = useGuideRun(roomId, "logistics", !hasFlights);

  useEffect(() => {
    let cancelled = false;

    const kickOff = async (): Promise<void> => {
      if (!isOwner) return;
      try {
        const tripId = await getServices().destination.getTripId(roomId);
        if (tripId && !cancelled) {
          await getServices().flight.startLogistics({ tripId, memberId });
        }
      } catch {
        // The run status below still shows what happened.
      }
    };
    void kickOff();

    const unsubscribe = getServices().flight.subscribeLogistics(
      roomId,
      (next) => {
        if (!cancelled) setState(next);
      },
    );
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [roomId, memberId, isOwner]);

  const advicePending = state.tiePending && state.tiebreak?.pending === true;
  const tieRun = useGuideRun(roomId, "tiebreak", advicePending);
  const [retryingAdvice, setRetryingAdvice] = useState(false);
  const retryAdvice = async (): Promise<void> => {
    setRetryingAdvice(true);
    try {
      await getServices().run.startRun(roomId, memberId, "tiebreak");
    } catch {
      // The leader can still choose without the advice.
    } finally {
      setRetryingAdvice(false);
      tieRun.refresh();
    }
  };

  const handleRetry = async (): Promise<void> => {
    setRetrying(true);
    try {
      const tripId = await getServices().destination.getTripId(roomId);
      if (tripId) {
        await getServices().flight.startLogistics({
          tripId,
          memberId,
          retry: true,
        });
      }
    } catch {
      // The run status will still show the failure.
    } finally {
      setRetrying(false);
      refresh();
    }
  };

  const handleVote = async (): Promise<void> => {
    if (!state.vote || selectedId === null || voting) return;
    setVoting(true);
    setError(null);
    try {
      await getServices().flight.castVote({
        voteSessionId: state.vote.voteSessionId,
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
    if (!state.tiebreak || deciding) return;
    setDeciding(true);
    setTieError(null);
    try {
      await getServices().flight.breakTie({
        voteSessionId: state.tiebreak.voteSessionId,
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

  const viewer = members.find((m) => m.id === memberId);
  const viewerReady = voted || viewer?.stageReady === true;
  const finishedEmpty = !hasFlights && run?.status === "completed";

  return (
    <StageChat>
      <GuideSay text="Destination locked! Now let's find the party's way there." />
      <GuideSay text="I'll search flights that fit your shared dates and budget." />

      {state.tiePending && state.tiebreak ? (
        <GuideMessage>
          <TiebreakPanel
            tiebreak={state.tiebreak}
            isOwner={isOwner}
            deciding={deciding}
            error={tieError}
            onBreakTie={(optionId) => {
              void handleBreakTie(optionId);
            }}
            thinking={
              <GuideThinking
                runType="tiebreak"
                run={tieRun.run}
                isOwner={isOwner}
                retrying={retryingAdvice}
                onRetry={() => {
                  void retryAdvice();
                }}
              />
            }
          />
        </GuideMessage>
      ) : hasFlights && viewerReady ? (
        <GuideMessage>
          <WaitingForParty members={members} what="flight vote" />
        </GuideMessage>
      ) : hasFlights ? (
        <GuideMessage>
          <div className="flex flex-col gap-16">
            <p className="font-body">
              Here are the best flights for the party. Pick the one that suits
              you, then lock in your vote.
            </p>
            <div className="flex flex-col gap-16">
              {state.options.map((option) => (
                <FlightMatchCard
                  key={option.id}
                  option={option}
                  selected={selectedId === option.id}
                  onToggle={(id) =>
                    setSelectedId((prev) => (prev === id ? null : id))
                  }
                />
              ))}
            </div>
            {error !== null ? (
              <p role="alert" className="font-body text-danger">
                {error}
              </p>
            ) : null}
            <PixelButton
              variant="primary"
              type="button"
              label={voting ? "CASTING…" : "LOCK IN VOTE"}
              disabled={selectedId === null || voting || state.vote === null}
              onClick={() => {
                void handleVote();
              }}
            />
          </div>
        </GuideMessage>
      ) : finishedEmpty ? (
        <GuideMessage>
          <div className="flex flex-col gap-16">
            <p className="font-body">
              {state.guideNote ??
                "I couldn't find flights that fit the party this time."}
            </p>
            {isOwner ? (
              <PixelButton
                variant="primary"
                label={retrying ? "SEARCHING AGAIN…" : "SEARCH AGAIN"}
                disabled={retrying}
                onClick={() => {
                  void handleRetry();
                }}
              />
            ) : (
              <p className="font-body text-muted">
                The party leader can ask the guide to search again.
              </p>
            )}
          </div>
        </GuideMessage>
      ) : (
        <GuideMessage>
          <div className="flex flex-col gap-16">
            <GuideThinking
              runType="logistics"
              run={run}
              isOwner={isOwner}
              retrying={retrying}
              onRetry={() => {
                void handleRetry();
              }}
            />
            {run?.status !== "failed" ? <SkeletonCards count={3} /> : null}
          </div>
        </GuideMessage>
      )}
    </StageChat>
  );
}

export default FlightStageContent;
