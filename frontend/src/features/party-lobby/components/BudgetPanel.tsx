"use client";

/**
 * BudgetPanel — the adventure sidebar budget readout.
 *
 * The party budget is not confirmed during setup, so this panel shows a
 * "Not set yet" placeholder instead of actual amounts. It becomes a real readout
 * (limit / estimated / remaining) once the trip budget is locked in. Purely
 * presentational; token styling only.
 */
import type { ReactElement } from "react";

import { PixelCard } from "@/components/PixelCard";

export function BudgetPanel(): ReactElement {
  return (
    <PixelCard title="Budget">
      <p className="font-body text-muted" data-testid="budget-panel">
        Not set yet
      </p>
    </PixelCard>
  );
}

export default BudgetPanel;
