"use client";

/**
 * StageChat — the chatbot-style message primitives that frame each planning stage.
 *
 * The NPC guide ("MILO") speaks in left-aligned bubbles; the party's own actions
 * echo as right-aligned bubbles; system notes (e.g. "Everyone's ready!") are
 * centred muted lines. Interactive stage content (forms, destination cards) is
 * dropped into a guide bubble via {@link GuidePanel}. Presentational only; token
 * styling.
 */
import type { ReactElement, ReactNode } from "react";

import { GuidePortrait } from "@/components/GuidePortrait";

const GUIDE_NAME = "MILO";

/** Shared vertical rhythm wrapper for a stage's message feed. */
export function StageChat({ children }: { children: ReactNode }): ReactElement {
  return <div className="flex flex-col gap-16">{children}</div>;
}

function GuideAvatar(): ReactElement {
  return (
    <span aria-hidden className="shrink-0 border-2 border-accent bg-bg-alt">
      <GuidePortrait scale={2} />
    </span>
  );
}

/** A guide (NPC) message bubble, optionally wrapping interactive content. */
export function GuideMessage({
  time,
  children,
}: {
  time?: string;
  children: ReactNode;
}): ReactElement {
  return (
    <div className="flex items-start gap-8">
      <GuideAvatar />
      <div className="flex flex-1 flex-col gap-8">
        <span className="flex items-center gap-8">
          <span className="font-display text-accent">{GUIDE_NAME}</span>
          {time ? <span className="font-body text-muted">{time}</span> : null}
        </span>
        <div className="border-l-2 border-primary bg-bg-alt p-16">{children}</div>
      </div>
    </div>
  );
}

/** A short line of guide dialogue. */
export function GuideSay({
  time,
  text,
}: {
  time?: string;
  text: string;
}): ReactElement {
  return (
    <GuideMessage time={time}>
      <p className="font-body">{text}</p>
    </GuideMessage>
  );
}

/** The party's own echoed action (right-aligned). */
export function PartySay({
  time,
  text,
}: {
  time?: string;
  text: string;
}): ReactElement {
  return (
    <div className="flex flex-col items-end gap-8">
      <div className="max-w-prose border-2 border-primary bg-primary-dark p-16 text-ink">
        <p className="font-body">{text}</p>
      </div>
      {time ? <span className="font-body text-muted">{time}</span> : null}
    </div>
  );
}

/** A centred system note (e.g. "Everyone's ready!"). */
export function SystemNote({ text }: { text: string }): ReactElement {
  return (
    <p className="font-body text-muted mx-auto rounded-none bg-bg-alt px-16 py-8 text-center">
      {text}
    </p>
  );
}
