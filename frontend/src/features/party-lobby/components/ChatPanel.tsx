"use client";

/**
 * ChatPanel — a local-only party chat surface for the SETUP stage.
 *
 * UI ONLY. There is no chat backend yet (the real chat service throws
 * `notImplemented`), so this component keeps an in-memory list of messages in
 * local state and makes NO service calls. It does not — and must not — fake
 * cross-user delivery: the viewer's typed messages are the only "user" bubbles,
 * seeded alongside one in-world NPC/system line from the Travel Guide.
 *
 * Structured so a real chat service can be dropped in later: messages carry a
 * stable shape ({@link LocalChatMessage}) and the submit path is a single
 * `appendMessage` seam that a service call could replace.
 *
 * Presentational + local state only: the only prop in is the viewer's display
 * name used to label their own messages.
 */
import { useId, useRef, useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";
import { PixelCard } from "@/components/PixelCard";
import { ChatBubble } from "@/components/ChatBubble";

/** The in-world speaker name for the seeded guide line. */
const GUIDE_NAME = "Travel Guide";

/** A single chat message held only in this component's local state. */
export interface LocalChatMessage {
  /** Stable id for list keys. */
  id: string;
  /** Who authored the line: the viewer, or the system/NPC guide. */
  author: "user" | "system";
  /** Display name shown with the message. */
  authorName: string;
  /** The message text. */
  text: string;
  /** ISO 8601 timestamp of when it was added locally. */
  at: string;
}

export interface ChatPanelProps {
  /** The viewer's display name, used to label their own messages. */
  viewerDisplayName: string;
}

let messageCounter = 0;
function nextMessageId(): string {
  messageCounter += 1;
  return `local-msg-${messageCounter}`;
}

export function ChatPanel({ viewerDisplayName }: ChatPanelProps): ReactElement {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [messages, setMessages] = useState<LocalChatMessage[]>(() => [
    {
      id: nextMessageId(),
      author: "system",
      authorName: GUIDE_NAME,
      text: "Welcome, adventurers! Gather your party and say hello while the quest takes shape.",
      at: new Date().toISOString(),
    },
  ]);
  const [draft, setDraft] = useState("");

  // The single append seam. A real chat service would replace this body with a
  // send + subscribe; the UI above it does not change.
  const appendMessage = (text: string): void => {
    setMessages((prev) => [
      ...prev,
      {
        id: nextMessageId(),
        author: "user",
        authorName: viewerDisplayName,
        text,
        at: new Date().toISOString(),
      },
    ]);
  };

  const submit = (): void => {
    const trimmed = draft.trim();
    if (trimmed.length === 0) return;
    appendMessage(trimmed);
    setDraft("");
    inputRef.current?.focus();
  };

  return (
    <PixelCard title="Party chat">
      <p className="font-body text-muted mb-8">
        Chat is local to your screen for now — messages aren&apos;t shared with
        the party yet.
      </p>

      <ul
        aria-label="Party chat messages"
        aria-live="polite"
        className="flex flex-col gap-8 mb-16"
      >
        {messages.map((message) => (
          <li key={message.id} className="flex flex-col gap-8">
            <span className="font-display text-accent">
              {message.author === "user"
                ? `${message.authorName} (you)`
                : message.authorName}
            </span>
            <ChatBubble sender={message.author === "user" ? "user" : "ai"}>
              {message.text}
            </ChatBubble>
          </li>
        ))}
      </ul>

      <form
        className="flex items-center gap-16"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <label htmlFor={inputId} className="sr-only">
          Message the party
        </label>
        <input
          id={inputId}
          ref={inputRef}
          type="text"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Say something to the party…"
          className="font-body text-ink bg-bg border-2 border-muted px-16 py-8 flex-1"
        />
        <PixelButton
          type="submit"
          variant="primary"
          label="Send"
          ariaLabel="Send message"
        />
      </form>
    </PixelCard>
  );
}

export default ChatPanel;
