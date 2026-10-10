"use client";

/**
 * SidebarPartyPanel — the party section of the adventure sidebar.
 *
 * Presentational only: data in via props, no data fetching, no service calls, no
 * network. Renders each party member as a small decorative CharacterSprite plus a
 * name label (Req 13.1, 13.3), fills the remaining capacity with visually distinct
 * empty party slots (Req 13.2), and offers two ways to invite, neither of which
 * makes a network request (Req 13.4): COPY INVITE LINK copies a link that opens the
 * join form with the room code filled in, and COPY next to the room code copies just
 * the code (Req 13.5). The button confirms for a moment ("LINK COPIED!"), and if the
 * browser refuses the clipboard the panel says so, with the code still on screen to
 * read out. Without a room code a placeholder stands in (Req 13.6).
 *
 * Composes the shared PixelCard, PixelButton, and CharacterSprite primitives and uses
 * design-token utility classes only.
 *
 * Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6.
 */
import { useEffect, useRef, useState, type ReactElement } from "react";

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
}

/** How long a "copied" confirmation stays on the button. */
const COPIED_MS = 2000;

/** The link that opens the join form with this room's code filled in. */
export function inviteLink(roomCode: string, origin: string): string {
  return `${origin}/?code=${encodeURIComponent(roomCode)}`;
}

export function SidebarPartyPanel({
  members,
  capacity,
  roomCode,
}: SidebarPartyPanelProps): ReactElement {
  const [copied, setCopied] = useState<"link" | "code" | "failed" | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);

  const copy = async (what: "link" | "code"): Promise<void> => {
    if (roomCode === null) return;
    clearTimeout(timer.current);
    try {
      await navigator.clipboard.writeText(
        what === "link" ? inviteLink(roomCode, window.location.origin) : roomCode,
      );
      setCopied(what);
      timer.current = setTimeout(() => setCopied(null), COPIED_MS);
    } catch {
      setCopied("failed");
    }
  };

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

      {roomCode !== null ? (
        <div className="mt-16 flex flex-col gap-8">
          <PixelButton
            label={copied === "link" ? "LINK COPIED!" : "COPY INVITE LINK"}
            variant="secondary"
            onClick={() => {
              void copy("link");
            }}
          />
          <div className="flex items-center justify-between gap-16">
            <p className="font-body">
              Room code:{" "}
              <span className="font-display text-accent">{roomCode}</span>
            </p>
            <PixelButton
              label={copied === "code" ? "COPIED!" : "COPY"}
              ariaLabel="Copy room code"
              variant="secondary"
              onClick={() => {
                void copy("code");
              }}
            />
          </div>
          <p role="status" aria-live="polite" className="font-body text-muted">
            {copied === "link"
              ? "Invite link copied. Send it to your party."
              : copied === "code"
                ? "Room code copied."
                : copied === "failed"
                  ? "Could not copy. Share the room code above instead."
                  : "Friends open the link, or enter the code on the join screen."}
          </p>
        </div>
      ) : (
        <p className="mt-16 font-body text-muted">No room code yet</p>
      )}
    </PixelCard>
  );
}

export default SidebarPartyPanel;
