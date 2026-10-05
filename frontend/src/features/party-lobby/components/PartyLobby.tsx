"use client";

/**
 * PartyLobby — the entry screen where an adventurer creates or joins a party.
 *
 * Presentational only: it receives all data via props and raises events via
 * callbacks (no service imports, no data fetching). RPG framing comes from the
 * shared {@link DialogueBox} NPC guide. Both forms submit on Enter, show pending
 * states, surface safe error/validation messages via an `aria-live` region, and
 * keep visible focus from the shared primitives.
 */
import { useState, type FormEvent, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import { PixelCard } from "@/components/PixelCard";
import { DialogueBox } from "@/components/DialogueBox";

import type { LobbyView } from "../hooks/usePartyLobby";

export interface PartyLobbyProps {
  /** Current lobby view; used to show pending states on the two actions. */
  view: LobbyView;
  /** Safe, player-facing error message, if any. */
  errorMessage?: string;
  /** Safe, player-facing validation message, if any. */
  validationMessage?: string;
  /** Create a new party with a room name and the owner's adventurer name. */
  onCreateParty: (name: string, ownerDisplayName: string) => void;
  /** Join an existing party with a code and the adventurer's name. */
  onJoinParty: (roomCode: string, displayName: string) => void;
}

export function PartyLobby({
  view,
  errorMessage,
  validationMessage,
  onCreateParty,
  onJoinParty,
}: PartyLobbyProps): ReactElement {
  const [adventurerName, setAdventurerName] = useState("");
  const [roomName, setRoomName] = useState("");
  const [roomCode, setRoomCode] = useState("");

  const creating = view === "creating";
  const joining = view === "joining";
  const busy = creating || joining;

  const handleCreate = (event: FormEvent): void => {
    event.preventDefault();
    onCreateParty(roomName, adventurerName);
  };

  const handleJoin = (event: FormEvent): void => {
    event.preventDefault();
    onJoinParty(roomCode, adventurerName);
  };

  const status = errorMessage ?? validationMessage;

  return (
    <main className="bg-bg text-ink font-body min-h-screen p-24">
      <div className="mx-auto flex max-w-xl flex-col gap-24">
        <h1 className="font-display text-accent text-center">
          PixelArt Trip Planner
        </h1>

        <DialogueBox
          speaker="Travel Guide"
          text="Welcome, adventurer! Name yourself, then start a new quest or join your party by its code."
        />

        {/* Shared adventurer-name field used by both actions. */}
        <PixelCard title="Your adventurer">
          <label className="font-display mb-8 block" htmlFor="adventurer-name">
            Adventurer name
          </label>
          <input
            id="adventurer-name"
            name="adventurer-name"
            type="text"
            autoComplete="off"
            value={adventurerName}
            onChange={(event) => setAdventurerName(event.target.value)}
            disabled={busy}
            className="bg-bg text-ink border-2 border-muted focus-visible:border-accent w-full p-8 focus-visible:outline-none"
          />
        </PixelCard>

        <PixelCard title="Start a new quest">
          <form onSubmit={handleCreate} className="flex flex-col gap-16">
            <label className="font-display block" htmlFor="room-name">
              Party name
            </label>
            <input
              id="room-name"
              name="room-name"
              type="text"
              autoComplete="off"
              value={roomName}
              onChange={(event) => setRoomName(event.target.value)}
              disabled={busy}
              className="bg-bg text-ink border-2 border-muted focus-visible:border-accent w-full p-8 focus-visible:outline-none"
            />
            <PixelButton
              type="submit"
              variant="primary"
              label={creating ? "Creating party..." : "Create Party"}
              disabled={busy}
            />
          </form>
        </PixelCard>

        <PixelCard title="Join your party">
          <form onSubmit={handleJoin} className="flex flex-col gap-16">
            <label className="font-display block" htmlFor="room-code">
              Party code
            </label>
            <input
              id="room-code"
              name="room-code"
              type="text"
              autoComplete="off"
              value={roomCode}
              onChange={(event) => setRoomCode(event.target.value)}
              disabled={busy}
              className="bg-bg text-ink border-2 border-muted focus-visible:border-accent w-full p-8 focus-visible:outline-none"
            />
            <PixelButton
              type="submit"
              variant="secondary"
              label={joining ? "Joining party..." : "Join Party"}
              disabled={busy}
            />
          </form>
        </PixelCard>

        {/* Status region: errors and validation messages are announced politely. */}
        <p
          role="status"
          aria-live="polite"
          className={`font-body min-h-8 ${status ? "text-warning" : ""}`}
        >
          {status ?? ""}
        </p>
      </div>
    </main>
  );
}

export default PartyLobby;
