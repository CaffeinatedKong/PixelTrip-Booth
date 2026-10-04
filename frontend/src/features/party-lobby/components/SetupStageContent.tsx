"use client";

/**
 * SetupStageContent — the real, working content for the SETUP stage.
 *
 * The room-code share card plus the live roster. Presentational only: data in
 * via props, events out via callbacks, no data fetching. Rendered both by
 * {@link PartyWaitingRoom} (standalone page) and by the stage shell inside the
 * pipeline, so the two never diverge. Contains no page chrome (no `<main>`,
 * heading, or leave button) — the host component supplies those.
 */
import { useRef, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import { PixelCard } from "@/components/PixelCard";
import { DialogueBox } from "@/components/DialogueBox";
import type { RoomMember, RoomSession } from "@/types";

import { RosterPanel } from "./RosterPanel";

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
    <div className="flex flex-col gap-24">
      <DialogueBox
        speaker="Travel Guide"
        text={
          isHost
            ? "Your party is forming. Share the code below so others can join the quest."
            : "You've joined the party. Wait here while the rest of the party gathers."
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

      <RosterPanel
        members={members}
        viewerDisplayName={session.member.displayName}
        viewerIsHost={isHost}
      />
    </div>
  );
}

export default SetupStageContent;
