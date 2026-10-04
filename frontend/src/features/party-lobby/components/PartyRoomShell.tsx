"use client";

/**
 * PartyRoomShell — the honest six-stage pipeline shell around a party room.
 *
 * Renders the stage stepper (derived from the room's `planningStage`) and the
 * current stage's content:
 * - SETUP is the real, working stage: the room-code share + live roster
 *   ({@link SetupStageContent}).
 * - Every other stage renders a {@link StagePlaceholder} — no fake data and no
 *   service calls, because those backends do not exist yet.
 *
 * Presentational only: it takes the session, roster, and copy flag via props and
 * raises copy/leave via callbacks. All data fetching stays in the hook/service
 * layer; this component never imports a service or Supabase.
 */
import type { ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import type { RoomMember, RoomSession } from "@/types";

import { buildStageSteps, isStageStubbed, stageMeta } from "../lib/stages";
import { ChatPanel } from "./ChatPanel";
import { SetupStageContent } from "./SetupStageContent";
import { StagePlaceholder } from "./StagePlaceholder";
import { StageStepper } from "./StageStepper";

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
  const steps = buildStageSteps(activeStage);

  return (
    <main className="bg-bg text-ink font-body min-h-screen p-24">
      <div className="mx-auto flex max-w-screen-2xl flex-col gap-24">
        <h1 className="font-display text-accent text-center">
          {session.room.name}
        </h1>

        <StageStepper steps={steps} />

        {isStageStubbed(activeStage) ? (
          <StagePlaceholder stage={stageMeta(activeStage)} />
        ) : (
          <>
            <SetupStageContent
              session={session}
              members={members}
              copied={copied}
              onCopyCode={onCopyCode}
            />
            <ChatPanel viewerDisplayName={session.member.displayName} />
          </>
        )}

        <PixelButton variant="danger" label="Leave party" onClick={onLeave} />
      </div>
    </main>
  );
}

export default PartyRoomShell;
