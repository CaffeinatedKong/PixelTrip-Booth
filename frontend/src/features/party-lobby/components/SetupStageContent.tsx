"use client";

/**
 * SetupStageContent — the real, working content for the SETUP stage.
 *
 * A responsive two-column SETUP screen: the left column holds the NPC dialogue,
 * the room-code share card, and the 8-bit {@link CharacterCreator}; the right
 * column is the {@link AdventureSidebar} whose PARTY panel reflects the LIVE room
 * roster (built from `members`). Presentational only: data in via props, events
 * out via callbacks, no data fetching. Trip name/dates/budget are feature-local
 * placeholders while the sidebar reads the live room code + roster from props.
 * Rendered both by {@link PartyWaitingRoom} (standalone page) and by the stage
 * shell inside the pipeline, so the two never diverge. Contains no page chrome
 * (no `<main>`, heading, or leave button) — the host component supplies those.
 */
import { useRef, useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import { PixelCard } from "@/components/PixelCard";
import { DialogueBox } from "@/components/DialogueBox";
import type { RoomMember, RoomSession } from "@/types";

import { CharacterCreator } from "./CharacterCreator";
import { AdventureSidebar } from "./AdventureSidebar";
import { WaitingForParty } from "./WaitingForParty";
import { buildAdventureView } from "../lib/adventureMocks";

export interface SetupStageContentProps {
  /** The active session (room + the viewer's member record). */
  session: RoomSession;
  /** Live roster of members in the room. */
  members: RoomMember[];
  /** True briefly after a successful copy of the room code. */
  copied: boolean;
  /** Copy the room code to the clipboard. */
  onCopyCode: () => void;
}

export function SetupStageContent({
  session,
  members,
  copied,
  onCopyCode,
}: SetupStageContentProps): ReactElement {
  const codeRef = useRef<HTMLSpanElement>(null);
  const isHost = session.member.role === "owner";
  // Party panel reflects the LIVE roster; trip/budget stay placeholder until a
  // trip backend exists.
  const adventure = buildAdventureView(members);

  // The viewer is done with SETUP once they save; the authoritative signal is
  // their own `stageReady` on the live roster, with a local flag for the instant
  // right after save (before the roster round-trips).
  const [savedLocally, setSavedLocally] = useState(false);
  const viewer = members.find((m) => m.id === session.member.id);
  const viewerReady = savedLocally || viewer?.stageReady === true;

  const selectCode = (): void => {
    const node = codeRef.current;
    if (!node) return;
    const selection = window.getSelection();
    if (!selection) return;
    const range = document.createRange();
    range.selectNodeContents(node);
    selection.removeAllRanges();
    selection.addRange(range);
  };

  return (
    <div className="flex flex-col gap-24 lg:grid lg:grid-cols-[2fr_1fr] lg:items-start lg:gap-24">
      {/* LEFT column: NPC dialogue, room-code share, and the character creator. */}
      <div className="flex flex-col gap-24">
        <DialogueBox
          speaker="Travel Guide"
          text={
            isHost
              ? "Your party is forming. Share the code below so others can join the quest."
              : "You've joined the party. Build your character while the rest gather."
          }
        />

        <PixelCard title="Party code">
          <p className="font-body mb-8">Share this code with your party:</p>
          <div className="flex items-center gap-16">
            <span
              ref={codeRef}
              data-testid="room-code"
              onClick={selectCode}
              className="font-display text-accent border-2 border-muted px-16 py-8 select-all"
            >
              {session.room.roomCode}
            </span>
            <PixelButton
              variant="option"
              label={copied ? "Copied!" : "Copy"}
              ariaLabel="Copy party code"
              onClick={onCopyCode}
            />
          </div>
          <p role="status" aria-live="polite" className="font-body min-h-8 mt-8">
            {copied ? "Party code copied to clipboard." : ""}
          </p>
        </PixelCard>

        {viewerReady ? (
          <WaitingForParty members={members} what="character" />
        ) : (
          <CharacterCreator
            session={session}
            onSaved={() => setSavedLocally(true)}
          />
        )}
      </div>

      {/* RIGHT column: the adventure sidebar (party panel = live roster). */}
      <AdventureSidebar adventure={adventure} roomSession={session} />
    </div>
  );
}

export default SetupStageContent;
