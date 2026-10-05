"use client";

/**
 * BudgetPanel — the adventure sidebar budget readout (Req 15).
 *
 * Presentational only: data in via the derived `BudgetView`, no data fetching.
 * Shows the budget limit, estimated expenditure, and remaining budget as whole
 * USD-style currency (e.g. "$0", "$1,500"). When the party is over budget it
 * swaps the remaining row for an over-budget state that shows the overage amount
 * plus a literal "OVER BUDGET" text label styled with the `danger` status token.
 *
 * Color is never the only signal: the "OVER BUDGET" text label always accompanies
 * the token color so the state reads without relying on color (Req 15.5).
 */
import type { ReactElement } from "react";

import { PixelCard } from "@/components/PixelCard";

import type { BudgetView } from "../types";

export interface BudgetPanelProps {
  /** The derived budget readout for the party. */
  budget: BudgetView;
}

/** Formats a whole-dollar amount as a USD-style string with no decimals, e.g. "$1,500". */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function BudgetPanel({ budget }: BudgetPanelProps): ReactElement {
  const { limit, estimated, remaining, isOverBudget, overageAmount } = budget;

  return (
    <PixelCard title="Budget">
      <dl className="flex flex-col gap-8" data-testid="budget-panel">
        <div className="flex items-center justify-between gap-16">
          <dt className="font-body text-muted">Limit</dt>
          <dd className="font-body">{formatCurrency(limit)}</dd>
        </div>
        <div className="flex items-center justify-between gap-16">
          <dt className="font-body text-muted">Estimated</dt>
          <dd className="font-body">{formatCurrency(estimated)}</dd>
        </div>
        {isOverBudget ? (
          <div className="flex items-center justify-between gap-16">
            <dt className="font-display text-danger">OVER BUDGET</dt>
            <dd className="font-body text-danger">
              {formatCurrency(overageAmount)} over
            </dd>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-16">
            <dt className="font-body text-muted">Remaining</dt>
            <dd className="font-body text-success">{formatCurrency(remaining)}</dd>
          </div>
        )}
      </dl>
    </PixelCard>
  );
}

export default BudgetPanel;
