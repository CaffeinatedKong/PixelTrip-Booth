"use client";

/**
 * PartyRoomShell — the room screen: a chatbot-style stage column on the left and
 * the persistent "YOUR ADVENTURE" sidebar on the right.
 *
 * The sidebar (party, destination/flight, budget, quest progress) stays on screen
 * across every stage. The left column shows the active stage as a guided NPC
 * conversation (SETUP character build, DISCOVER destination choice, ...). There is
 * no separate top stepper (the sidebar already shows quest progress) and no
 * bottom party chat; the stage conversation IS the chat.
 *
 * Presentational only: session, roster, and copy flag in via props; copy/leave
 * out via callbacks. No service imports here.
 */
import type { ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import type { RoomMember, RoomSession } from "@/types";

import { AdventureSidebar } from "./AdventureSidebar";
import { buildAdventureView } from "../lib/adventureMocks";
import { stageMeta } from "../lib/stages";
import { SetupStageContent } from "./SetupStageContent";
import { DestinationStageContent } from "./DestinationStageContent";
import { StagePlaceholder } from "./StagePlaceholder";

export interface PartyRoomShellProps {
  /** The active room session (room + the viewer's member record). */
  session: RoomSession;
  /** Live roster of members in the room. */
  members: RoomMember[];
  /** True briefly after a successful copy of the room code. */
  copied: boolean;
  /** Copy the room code to the clipboard. */
  onCopyCode: () => void;
  /** Leave the party and return to the entry screen (local only). */
  onLeave: () => void;
}

export function PartyRoomShell({
  session,
  members,
  copied,
  onCopyCode,
  onLeave,
}: PartyRoomShellProps): ReactElement {
  const activeStage = session.room.planningStage;
  const adventure = buildAdventureView(members);

  return (
    <main className="bg-bg text-ink font-body min-h-screen p-24">
      <div className="mx-auto flex max-w-screen-2xl flex-col gap-24">
        <div className="flex items-center justify-between gap-16">
          <h1 className="font-display text-accent">{session.room.name}</h1>
          <PixelButton variant="danger" label="Leave party" onClick={onLeave} />
        </div>

        {/* Two columns: chatbot-style stage flow (left) + persistent sidebar (right). */}
        <div className="flex flex-col gap-24 lg:grid lg:grid-cols-[2fr_1fr] lg:items-start lg:gap-24">
          <div className="flex flex-col gap-24">
            {activeStage === "setup" ? (
              <SetupStageContent
                session={session}
                members={members}
                copied={copied}
                onCopyCode={onCopyCode}
              />
            ) : activeStage === "discover" ? (
              <DestinationStageContent session={session} members={members} />
            ) : (
              <StagePlaceholder stage={stageMeta(activeStage)} />
            )}
          </div>

          <AdventureSidebar adventure={adventure} roomSession={session} />
        </div>
      </div>
    </main>
  );
}

export default PartyRoomShell;
