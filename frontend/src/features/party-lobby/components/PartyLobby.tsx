"use client";

/**
 * PartyLobby — the entry screen where an adventurer creates or joins a party.
 *
 * A single centred card with a Create Room / Join Room tab toggle, a shared
 * "Display name" field, a contextual second field (party name when creating, room
 * code when joining), and one primary action button. Branded with the PixelTrip
 * mark + tagline.
 *
 * Presentational only: data in via props, events out via callbacks (no service
 * imports, no data fetching). Submits on Enter, shows pending states, and surfaces
 * safe error/validation messages via an `aria-live` region. Token styling only.
 */
import { useState, type FormEvent, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";

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

type Tab = "create" | "join";

const INPUT_CLASSES =
  "font-body text-ink bg-bg border-2 border-muted w-full px-16 py-8 focus-visible:outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

export function PartyLobby({
  view,
  errorMessage,
  validationMessage,
  onCreateParty,
  onJoinParty,
}: PartyLobbyProps): ReactElement {
  const [tab, setTab] = useState<Tab>("create");
  const [displayName, setDisplayName] = useState("");
  const [roomName, setRoomName] = useState("");
  const [roomCode, setRoomCode] = useState("");

  const creating = view === "creating";
  const joining = view === "joining";
  const busy = creating || joining;

  const handleSubmit = (event: FormEvent): void => {
    event.preventDefault();
    if (tab === "create") {
      onCreateParty(roomName, displayName);
    } else {
      onJoinParty(roomCode, displayName);
    }
  };

  const status = errorMessage ?? validationMessage;

  const tabClass = (active: boolean): string =>
    `font-display flex-1 border-2 px-16 py-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg ${
      active ? "border-primary bg-primary text-bg" : "border-ink bg-bg-alt text-ink"
    }`;

  const buttonLabel =
    tab === "create"
      ? creating
        ? "Creating room…"
        : "Create room"
      : joining
        ? "Joining room…"
        : "Join room";

  return (
    <main className="bg-bg text-ink font-body flex min-h-screen items-center justify-center p-24">
      <div className="flex w-full max-w-md flex-col items-center gap-24">
        {/* Branding */}
        <div className="flex flex-col items-center gap-8 text-center">
          <span aria-hidden className="text-4xl leading-none">
            🎮
          </span>
          <h1 className="font-display text-primary">PixelTrip</h1>
          <p className="font-body text-muted">
            Collaborative AI travel planning with 8-bit personas.
          </p>
        </div>

        {/* Single card with the tab toggle + form */}
        <section className="bg-bg-alt border-2 border-ink w-full p-24">
          {/* Tab toggle */}
          <div
            className="mb-24 flex gap-8"
            role="tablist"
            aria-label="Create or join a room"
          >
            <button
              type="button"
              role="tab"
              aria-selected={tab === "create"}
              onClick={() => setTab("create")}
              disabled={busy}
              className={tabClass(tab === "create")}
            >
              Create Room
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "join"}
              onClick={() => setTab("join")}
              disabled={busy}
              className={tabClass(tab === "join")}
            >
              Join Room
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-24">
            {/* Shared display name */}
            <div className="flex flex-col gap-8">
              <label htmlFor="display-name" className="font-display text-ink">
                Display name
              </label>
              <input
                id="display-name"
                name="display-name"
                type="text"
                autoComplete="off"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                disabled={busy}
                className={INPUT_CLASSES}
              />
            </div>

            {/* Contextual second field */}
            {tab === "create" ? (
              <div className="flex flex-col gap-8">
                <label htmlFor="room-name" className="font-display text-ink">
                  Room name
                </label>
                <input
                  id="room-name"
                  name="room-name"
                  type="text"
                  autoComplete="off"
                  value={roomName}
                  onChange={(event) => setRoomName(event.target.value)}
                  disabled={busy}
                  placeholder="THE WANDERING PARTY"
                  className={INPUT_CLASSES}
                />
              </div>
            ) : (
              <div className="flex flex-col gap-8">
                <label htmlFor="room-code" className="font-display text-ink">
                  Room code
                </label>
                <input
                  id="room-code"
                  name="room-code"
                  type="text"
                  autoComplete="off"
                  value={roomCode}
                  onChange={(event) => setRoomCode(event.target.value)}
                  disabled={busy}
                  placeholder="E.G. AB12CD"
                  className={INPUT_CLASSES}
                />
              </div>
            )}

            <PixelButton
              type="submit"
              variant="option"
              label={buttonLabel}
              disabled={busy}
              className="w-full"
            />
          </form>
        </section>

        {/* Status region: errors / validation announced politely. */}
        <p
          role="status"
          aria-live="polite"
          className={`font-body min-h-8 text-center ${status ? "text-warning" : "text-muted"}`}
        >
          {status ?? "No account needed · Share a room code to travel together."}
        </p>
      </div>
    </main>
  );
}

export default PartyLobby;
