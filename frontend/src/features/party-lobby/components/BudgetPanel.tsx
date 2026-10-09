"use client";

/**
 * BudgetPanel — the adventure sidebar budget readout.
 *
 * Shows the party's per-person budget from `GET /trips/{tripId}/budget`:
 *
 * - a hard limit (the lowest amount a member typed) and who set it, or, when nobody
 *   typed one, the budget level as a guide (its daily range and a trip estimate);
 * - what the trip is estimated to cost so far (stay, flight, activities) and what
 *   is left, filling in as votes lock a destination and a flight.
 *
 * "Not set yet" until there is a budget. Purely presentational; token styling only.
 */
import type { ReactElement } from "react";

import { PixelCard } from "@/components/PixelCard";
import type { DailyRange, TripBudget } from "@/services/budget.contract";

const LEVEL_LABELS = { low: "Low", medium: "Medium", high: "High" } as const;

function money(currency: string, amount: number): string {
  return `${currency} ${Math.round(amount).toLocaleString("en-SG")}`;
}

function range(currency: string, band: DailyRange): string {
  return band.high === null
    ? `${currency} ${band.low}+`
    : `${currency} ${band.low}–${band.high}`;
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "danger" | "success";
}): ReactElement {
  const toneClass =
    tone === "danger"
      ? "text-danger"
      : tone === "success"
        ? "text-success"
        : "";
  return (
    <div className="flex justify-between gap-16">
      <dt className="text-muted">{label}</dt>
      <dd className={toneClass}>{value}</dd>
    </div>
  );
}

export interface BudgetPanelProps {
  /** The party's budget, or `null` when it is not known yet. */
  budget?: TripBudget | null;
}

export function BudgetPanel({ budget = null }: BudgetPanelProps): ReactElement {
  const hasLevel = budget?.level != null && budget.dailyRange != null;
  if (!budget || (!budget.isHardLimit && !hasLevel)) {
    return (
      <PixelCard title="Budget">
        <p className="font-body text-muted" data-testid="budget-panel">
          Not set yet
        </p>
      </PixelCard>
    );
  }

  const { currency, estimates } = budget;
  const level =
    budget.level && budget.dailyRange
      ? `${LEVEL_LABELS[budget.level]} · ~${range(currency, budget.dailyRange)}/day`
      : null;

  return (
    <PixelCard title="Budget">
      <div className="font-body flex flex-col gap-8" data-testid="budget-panel">
        {budget.isHardLimit && budget.limit !== null ? (
          <p>
            <strong className="font-display text-accent">
              {money(currency, budget.limit)}
            </strong>{" "}
            per person
            {budget.limitSetBy ? (
              <span className="text-muted"> (lowest: {budget.limitSetBy})</span>
            ) : null}
          </p>
        ) : (
          <p>
            <strong className="font-display text-accent">Guide only</strong>{" "}
            <span className="text-muted">(no amount set)</span>
          </p>
        )}
        {level ? <p className="text-muted">Style: {level}</p> : null}
        {!budget.isHardLimit && budget.levelEstimate !== null && budget.days ? (
          <p className="text-muted">
            ~{money(currency, budget.levelEstimate)} for {budget.days} days,
            excluding flights
          </p>
        ) : null}

        {estimates.total !== null ? (
          <dl className="flex flex-col gap-8 border-t-2 border-ink pt-8">
            {estimates.stay !== null ? (
              <Row
                label="Stay & food (est.)"
                value={`~${money(currency, estimates.stay)}`}
              />
            ) : null}
            {estimates.flight !== null ? (
              <Row label="Flight" value={money(currency, estimates.flight)} />
            ) : null}
            {estimates.activities !== null ? (
              <Row
                label="Activities (est.)"
                value={`~${money(currency, estimates.activities)}`}
              />
            ) : null}
            <Row
              label="Total so far"
              value={money(currency, estimates.total)}
            />
            {budget.remaining !== null ? (
              <Row
                label={budget.isOverBudget ? "Over budget" : "Remaining"}
                value={money(currency, Math.abs(budget.remaining))}
                tone={budget.isOverBudget ? "danger" : "success"}
              />
            ) : null}
          </dl>
        ) : null}
      </div>
    </PixelCard>
  );
}

export default BudgetPanel;
