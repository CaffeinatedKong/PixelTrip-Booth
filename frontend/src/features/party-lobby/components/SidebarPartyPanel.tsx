/**
 * SidebarPartyPanel — the party section of the adventure sidebar.
 *
 * Presentational only: data in via props, no data fetching, no service calls, no
 * network. Renders each party member as a small decorative CharacterSprite plus a
 * name label (Req 13.1, 13.3), fills the remaining capacity with visually distinct
 * empty party slots (Req 13.2), and surfaces an "INVITE MEMBERS" affordance that
 * performs no network request (Req 13.4). When a room code is available it is shown
 * within/next to the invite affordance (Req 13.5); otherwise a placeholder stands in
 * for it (Req 13.6).
 *
 * Composes the shared PixelCard, PixelButton, and CharacterSprite primitives and uses
 * design-token utility classes only.
 *
 * Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6.
 */
import type { ReactElement } from "react";

import { PixelCard } from "@/components/PixelCard";
import { PixelButton } from "@/components/PixelButton";
import { CharacterSprite } from "@/components/CharacterSprite";
import type { PartyMemberView } from "../types";
import { BASE_LAYER } from "../lib/characterLayers";

export interface SidebarPartyPanelProps {
  /** The party members currently in the room. */
  members: readonly PartyMemberView[];
  /** The party's displayed capacity; drives how many empty slots render. */
  capacity: number;
  /** The active room code, or null when no room session is available. */
  roomCode: string | null;
  /** Invite handler. Performs NO network request (parent handler is also network-free). */
  onInvite: () => void;
}

export function SidebarPartyPanel({
  members,
  capacity,
  roomCode,
  onInvite,
}: SidebarPartyPanelProps): ReactElement {
  const emptySlotCount = Math.max(0, capacity - members.length);
  const emptySlots = Array.from({ length: emptySlotCount }, (_, index) => index);

  return (
    <PixelCard title="PARTY">
      <ul className="flex flex-col gap-8" aria-label="Party members">
        {members.map((member) => (
          <li
            key={member.id}
            className="flex items-center gap-16 border-2 border-muted p-8"
          >
            <CharacterSprite
              spriteKey={member.spriteKey}
              label={`${member.displayName}'s character`}
              layers={[BASE_LAYER]}
              size="sm"
              decorative
            />
            <span className="font-body">{member.displayName}</span>
          </li>
        ))}
        {emptySlots.map((slot) => (
          <li
            key={`empty-slot-${slot}`}
            className="flex items-center gap-16 border-2 border-dashed border-muted p-8 text-muted"
          >
            <span
              aria-hidden
              className="w-16 h-16 border-2 border-dashed border-muted bg-bg"
            />
            <span className="font-body">Empty slot</span>
          </li>
        ))}
      </ul>

      <div className="mt-16 flex flex-col gap-8">
        <PixelButton
          label="INVITE MEMBERS"
          variant="secondary"
          onClick={onInvite}
        />
        {roomCode !== null ? (
          <p className="font-body">
            Room code: <span className="font-display text-accent">{roomCode}</span>
          </p>
        ) : (
          <p className="font-body text-muted">No room code yet</p>
        )}
      </div>
    </PixelCard>
  );
}

export default SidebarPartyPanel;
