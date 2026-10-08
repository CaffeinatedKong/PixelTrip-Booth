"use client";

/**
 * DestinationStageContent — the DISCOVER stage: choose a destination.
 *
 * The AI will recommend destinations from the party's combined preferences; until
 * that backend lands this screen uses mock recommendation cards. The flow mirrors
 * SETUP: the viewer picks a destination, their choice locks, and we show
 * "waiting for other party members" (driven by the live roster `stageReady`) until
 * everyone has chosen and the party advances.
 *
 * Presentational: data in via props, no data fetching. The right column reuses the
 * {@link AdventureSidebar}; the left shows the destination picker or the waiting
 * panel. (Casting a real vote + advancing is wired when the voting backend is
 * connected here.)
 */
import { useState, type ReactElement } from "react";

import { DialogueBox } from "@/components/DialogueBox";
import { PixelCard } from "@/components/PixelCard";
import type { RoomMember, RoomSession } from "@/types";

import { AdventureSidebar } from "./AdventureSidebar";
import { WaitingForParty } from "./WaitingForParty";
import { VibeCardGroup } from "./VibeCardGroup";
import { buildAdventureView } from "../lib/adventureMocks";
import { MOCK_DESTINATION_OPTIONS } from "../lib/destinationMocks";

export interface DestinationStageContentProps {
  /** The active session (room + the viewer's member record). */
  session: RoomSession;
  /** Live roster of members in the room. */
  members: RoomMember[];
}

export function DestinationStageContent({
  session,
  members,
}: DestinationStageContentProps): ReactElement {
  const adventure = buildAdventureView(members);

  // Local single-pick (the backend vote/advance is wired later). Once the viewer
  // confirms, their choice locks and the waiting panel is shown.
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  const viewer = members.find((m) => m.id === session.member.id);
  const viewerReady = confirmed || viewer?.stageReady === true;

  return (
    <div className="flex flex-col gap-24 lg:grid lg:grid-cols-[2fr_1fr] lg:items-start lg:gap-24">
      {/* LEFT column: NPC prompt + destination picker (or waiting panel). */}
      <div className="flex flex-col gap-24">
        <DialogueBox
          speaker="Travel Guide"
          text="The party is formed! Where shall our journey begin? Cast your vote, adventurer."
        />

        {viewerReady ? (
          <WaitingForParty members={members} what="destination pick" />
        ) : (
          <PixelCard title="Choose your destination">
            <VibeCardGroup
              legend="Where should the party go?"
              mode="single"
              options={MOCK_DESTINATION_OPTIONS}
              selectedIds={selectedId ? [selectedId] : []}
              onToggle={(id) =>
                setSelectedId((prev) => (prev === id ? null : id))
              }
            />
            <div className="mt-16">
              <button
                type="button"
                disabled={selectedId === null}
                onClick={() => setConfirmed(true)}
                className="font-display border-2 border-ink px-16 py-8 bg-primary text-bg disabled:bg-muted disabled:text-bg-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
              >
                LOCK IN VOTE
              </button>
            </div>
          </PixelCard>
        )}
      </div>

      {/* RIGHT column: the adventure sidebar (party panel = live roster). */}
      <AdventureSidebar adventure={adventure} roomSession={session} />
    </div>
  );
}

export default DestinationStageContent;
