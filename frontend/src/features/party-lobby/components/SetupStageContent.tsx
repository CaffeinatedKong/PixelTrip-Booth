"use client";

/**
 * SetupStageContent — SETUP as a chatbot-style flow (left column only; the shell
 * owns the persistent sidebar).
 *
 * MILO (the NPC guide) frames the stage in chat bubbles: share the room code,
 * then build your travel character. The {@link CharacterCreator} lives inside a
 * guide bubble; once the viewer saves, it swaps to the "waiting for the party"
 * panel. Presentational: data in via props, events out via callbacks.
 */
import { useRef, useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import type { RoomMember, RoomSession } from "@/types";

import { CharacterCreator } from "./CharacterCreator";
import { WaitingForParty } from "./WaitingForParty";
import { StageChat, GuideSay, GuideMessage } from "./StageChat";

export interface SetupStageContentProps {
  /** The active session (room + the viewer's member record). */
  session: RoomSession;
  /** Called once the viewer's character is saved. */
  onCharacterSaved?: () => void;
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
  onCharacterSaved,
}: SetupStageContentProps): ReactElement {
  const codeRef = useRef<HTMLSpanElement>(null);
  const isHost = session.member.role === "owner";

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
    <StageChat>
      <GuideSay
        text={
          isHost
            ? "Welcome, host! Share your room code so the party can gather."
            : "Welcome to the party! Build your travel character while the rest gather."
        }
      />

      {/* Room-code share lives in a guide bubble. */}
      <GuideMessage>
        <div className="flex flex-col gap-8">
          <p className="font-body">Share this code with your party:</p>
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
        </div>
      </GuideMessage>

      <GuideSay text="Build your travel character. Your budget and interests shape where we go." />

      {viewerReady ? (
        <GuideMessage>
          <WaitingForParty members={members} what="character" />
        </GuideMessage>
      ) : (
        <GuideMessage>
          <CharacterCreator
            session={session}
            onSaved={() => {
              setSavedLocally(true);
              onCharacterSaved?.();
            }}
          />
        </GuideMessage>
      )}
    </StageChat>
  );
}

export default SetupStageContent;
