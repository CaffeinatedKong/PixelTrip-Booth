"use client";

/**
 * DestinationMatchCard — a rich recommendation card for one AI-suggested option.
 *
 * Renders the title, an optional FIT score badge, a "WHY THIS FITS" blurb,
 * highlight tags, an optional trade-off note, a Select action, and an expandable
 * "View full details" section. Every enrichment field (score, tags, trade-off,
 * details) is OPTIONAL: the backend AI fills `meta` over time, and this card
 * degrades gracefully — showing just the title + description + Select until the
 * backend provides more. Presentational only; token styling.
 */
import { useState, type ReactElement } from "react";

import { PixelButton } from "@/components/PixelButton";

/** One recommendation option; `meta` is the AI's free-form detail bag. */
export interface DestinationMatch {
  id: string;
  title: string;
  description?: string;
  meta?: Record<string, unknown>;
}

export interface DestinationMatchCardProps {
  option: DestinationMatch;
  selected: boolean;
  onToggle: (id: string) => void;
}

/** Read a numeric fit score from any of the keys the backend might use. */
function readScore(meta: Record<string, unknown> | undefined): number | null {
  if (!meta) return null;
  for (const key of ["score", "fit", "fitScore", "match"]) {
    const value = meta[key];
    if (typeof value === "number" && Number.isFinite(value)) return Math.round(value);
    if (typeof value === "string" && value.trim() !== "" && !Number.isNaN(Number(value))) {
      return Math.round(Number(value));
    }
  }
  return null;
}

/** Read a string from the first present key. */
function readText(
  meta: Record<string, unknown> | undefined,
  keys: readonly string[],
): string | null {
  if (!meta) return null;
  for (const key of keys) {
    const value = meta[key];
    if (typeof value === "string" && value.trim() !== "") return value;
  }
  return null;
}

/** Read a string[] from the first present key. */
function readTags(
  meta: Record<string, unknown> | undefined,
  keys: readonly string[],
): string[] {
  if (!meta) return [];
  for (const key of keys) {
    const value = meta[key];
    if (Array.isArray(value)) {
      return value
        .map((v) => (typeof v === "string" ? v : String(v)))
        .filter((v) => v.trim() !== "");
    }
  }
  return [];
}

export function DestinationMatchCard({
  option,
  selected,
  onToggle,
}: DestinationMatchCardProps): ReactElement {
  const [open, setOpen] = useState(false);
  const meta = option.meta;

  const score = readScore(meta);
  const why =
    readText(meta, ["whyThisFits", "why", "reason"]) ?? option.description ?? null;
  const tags = readTags(meta, ["tags", "highlights", "pros"]);
  const tradeOff = readText(meta, ["tradeOff", "tradeoff", "con", "warning"]);
  const details = readText(meta, ["details", "fullDetails", "longDescription"]);

  return (
    <article
      className={`flex flex-col gap-16 border-2 p-16 ${
        selected ? "border-accent bg-bg-alt" : "border-muted bg-bg-alt"
      }`}
    >
      {/* Header: title + fit score */}
      <header className="flex items-center justify-between gap-16">
        <h3 className="font-display text-accent">{option.title}</h3>
        {score !== null ? (
          <span className="font-display border-2 border-success bg-success px-8 py-8 text-bg">
            FIT {score}/100
          </span>
        ) : null}
      </header>

      {/* Why this fits */}
      {why ? (
        <div className="flex flex-col gap-8">
          <span className="font-display text-muted">WHY THIS FITS</span>
          <p className="font-body">{why}</p>
        </div>
      ) : null}

      {/* Highlight tags */}
      {tags.length > 0 ? (
        <ul className="flex flex-wrap gap-8">
          {tags.map((tag) => (
            <li
              key={tag}
              className="font-body border-2 border-success bg-bg px-8 py-8 text-success"
            >
              {tag}
            </li>
          ))}
        </ul>
      ) : null}

      {/* Trade-off */}
      {tradeOff ? (
        <div className="flex flex-col gap-8">
          <span className="font-display text-warning">TRADE-OFF</span>
          <p className="font-body text-muted">{tradeOff}</p>
        </div>
      ) : null}

      {/* Actions */}
      <div className="flex flex-col gap-8">
        <PixelButton
          variant={selected ? "primary" : "option"}
          label={selected ? "Selected" : "Select"}
          ariaPressed={selected}
          onClick={() => onToggle(option.id)}
        />
        {details ? (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((prev) => !prev)}
            className="font-body text-muted border-2 border-muted px-16 py-8 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            {open ? "▲ Hide details" : "▼ View full details"}
          </button>
        ) : null}
        {open && details ? <p className="font-body">{details}</p> : null}
      </div>
    </article>
  );
}

export default DestinationMatchCard;
