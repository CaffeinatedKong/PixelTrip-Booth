"use client";

/**
 * TripDatesDialog — the party leader changes how long the trip is and when it
 * starts. Opened from the sidebar TRIP DATES card and from the flight screen.
 *
 * The leader picks a length (stepper, within the allowed range) and a start date;
 * the end date, the stay's estimated cost and what that leaves of the budget
 * update as they go. Dates must sit inside when the whole party is free; the
 * problem, if any, is shown under the field. Saving stores the dates and starts
 * a fresh flight search, since flights found so far were for the old dates.
 *
 * A modal dialog: focus moves in on open and back on close, Tab stays inside,
 * and Esc or CANCEL closes it without saving.
 */
import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactElement,
} from "react";

import { PixelButton } from "@/components/PixelButton";
import { ApiError } from "@/lib/errors";
import { getServices } from "@/services";
import type { TripDates } from "@/services/tripDates.contract";

import {
  addDays,
  formatDay,
  formatWindows,
  stayPreview,
  todayIso,
  tripDatesProblem,
} from "../lib/tripDates";

const INPUT_CLASSES =
  "font-body text-ink bg-bg border-2 border-muted px-16 py-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

const FOCUSABLE = "button:not([disabled]), input:not([disabled])";

function money(amount: number): string {
  return `SGD ${Math.abs(amount).toLocaleString("en-SG")}`;
}

export interface TripDatesDialogProps {
  roomId: string;
  memberId: string;
  dates: TripDates;
  onClose: () => void;
  /** Called after the dates are saved (the new flight search has been asked for). */
  onSaved?: () => void;
}

export function TripDatesDialog({
  roomId,
  memberId,
  dates,
  onClose,
  onSaved,
}: TripDatesDialogProps): ReactElement {
  const titleId = useId();
  const startId = useId();
  const helpId = useId();
  const errorId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const startRef = useRef<HTMLInputElement>(null);

  const today = todayIso();
  const [days, setDays] = useState(
    Math.min(dates.maxDays, Math.max(dates.minDays, dates.tripDays ?? 5)),
  );
  const [start, setStart] = useState(
    dates.tripStart ?? dates.windows[0]?.start ?? today,
  );
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Move focus in on open; hand it back to whatever opened the dialog on close.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    startRef.current?.focus();
    return () => opener?.focus?.();
  }, []);

  const problem = tripDatesProblem(dates, days, start, today);
  const validStart = /^\d{4}-\d{2}-\d{2}$/.test(start);
  const end = validStart ? addDays(start, days - 1) : null;
  const preview = stayPreview(dates, days);
  const unchanged = days === dates.tripDays && start === dates.tripStart;
  const showProblem = problem !== null && (touched || saveError !== null);

  const earliest = dates.windows.reduce<string | undefined>(
    (min, w) => (min === undefined || w.start < min ? w.start : min),
    undefined,
  );
  const latestEnd = dates.windows.reduce<string | undefined>(
    (max, w) => (max === undefined || w.end > max ? w.end : max),
    undefined,
  );

  const changeDays = (next: number): void => {
    setDays(Math.min(dates.maxDays, Math.max(dates.minDays, next)));
    setTouched(true);
    setSaveError(null);
  };

  const handleSave = async (): Promise<void> => {
    setTouched(true);
    if (problem !== null || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      await getServices().tripDates.changeDates(roomId, {
        memberId,
        days,
        start,
      });
    } catch (err) {
      setSaveError(
        err instanceof ApiError &&
          (err.code === "INVALID_TRIP_DATES" || err.code === "TRIP_DATES_LOCKED")
          ? err.message
          : "Could not save the dates. Please try again.",
      );
      setSaving(false);
      return;
    }
    try {
      await getServices().run.startRun(roomId, memberId, "logistics");
    } catch {
      // The dates are saved; the flight screen offers SEARCH AGAIN.
    }
    setSaving(false);
    onSaved?.();
    onClose();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === "Escape" && !saving) {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const items = panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE);
    if (!items || items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-bg/80 p-16">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={handleKeyDown}
        className="flex w-full max-w-lg flex-col gap-16 border-4 border-ink bg-bg-alt p-24 text-ink"
      >
        <div className="flex flex-col gap-8">
          <h2 id={titleId} className="font-display text-accent">
            CHANGE TRIP DATES
          </h2>
          {dates.destination ? (
            <p className="font-body text-muted">{dates.destination}</p>
          ) : null}
        </div>

        <div className="flex flex-col gap-8">
          <span className="font-display" id={`${titleId}-days`}>
            Trip length
          </span>
          <div
            role="group"
            aria-labelledby={`${titleId}-days`}
            className="flex items-center gap-16"
          >
            <PixelButton
              variant="secondary"
              label="−"
              ariaLabel="One day shorter"
              disabled={saving || days <= dates.minDays}
              onClick={() => changeDays(days - 1)}
            />
            <output
              aria-live="polite"
              className="font-display text-accent"
              data-testid="trip-days"
            >
              {days} DAYS
            </output>
            <PixelButton
              variant="secondary"
              label="+"
              ariaLabel="One day longer"
              disabled={saving || days >= dates.maxDays}
              onClick={() => changeDays(days + 1)}
            />
          </div>
          <p className="font-body text-muted">
            {dates.minDays} to {dates.maxDays} days.
          </p>
        </div>

        <div className="flex flex-col gap-8">
          <label htmlFor={startId} className="font-display">
            Start date
          </label>
          <input
            ref={startRef}
            id={startId}
            type="date"
            value={start}
            min={earliest && earliest > today ? earliest : today}
            max={latestEnd ? addDays(latestEnd, -(days - 1)) : undefined}
            disabled={saving}
            aria-invalid={showProblem}
            aria-describedby={showProblem ? `${helpId} ${errorId}` : helpId}
            onChange={(event) => {
              setStart(event.target.value);
              setSaveError(null);
            }}
            onBlur={() => setTouched(true)}
            className={INPUT_CLASSES}
          />
          <p id={helpId} className="font-body text-muted">
            {dates.windows.length > 0
              ? `The whole party is free ${formatWindows(dates.windows)}.`
              : "The party has no shared free dates yet."}
          </p>
          {showProblem ? (
            <p id={errorId} role="alert" className="font-body text-danger">
              {problem}
            </p>
          ) : null}
        </div>

        <div
          className="flex flex-col gap-8 border-2 border-ink bg-bg p-16 font-body"
          data-testid="trip-dates-preview"
        >
          {end !== null ? (
            <p>
              <strong className="font-display text-accent">
                {formatDay(start)} – {formatDay(end)}
              </strong>
            </p>
          ) : null}
          {preview !== null ? (
            <p className={preview.tight ? "text-warning" : "text-muted"}>
              Stay and food about {money(preview.stay)} per person
              {preview.left === null
                ? "."
                : preview.left >= 0
                  ? `, leaving about ${money(preview.left)} for flights and activities.`
                  : `, which is ${money(preview.left)} over the party's budget.`}
              {preview.tight && preview.left !== null && preview.left >= 0
                ? " That is tight: flights may come out over budget."
                : ""}
            </p>
          ) : null}
        </div>

        <p className="font-body text-muted">
          Saving starts a new flight search for these dates. Flights and votes
          from the old dates are cleared.
        </p>

        {saveError !== null ? (
          <p role="alert" className="font-body text-danger">
            {saveError}
          </p>
        ) : null}

        <div className="flex flex-wrap gap-16">
          <PixelButton
            variant="primary"
            label={saving ? "SAVING…" : "SAVE AND SEARCH FLIGHTS"}
            disabled={saving || unchanged || (touched && problem !== null)}
            onClick={() => {
              void handleSave();
            }}
          />
          <PixelButton
            variant="secondary"
            label="CANCEL"
            disabled={saving}
            onClick={onClose}
          />
        </div>
      </div>
    </div>
  );
}

export default TripDatesDialog;
