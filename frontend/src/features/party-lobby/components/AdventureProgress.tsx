"use client";

/**
 * AdventureProgress — the six-stage quest progress stepper.
 *
 * Purely presentational: it renders the ordered {@link StageStep} model it is
 * given (built by `buildStageSteps(planningStage)` in the parent) and marks each
 * stage complete / current / upcoming. It does not call `buildStageSteps` itself
 * and performs no data fetching.
 *
 * The current stage is distinguished from complete / upcoming stages by a text
 * status label and an `aria-current="step"` marker IN ADDITION TO a theme-token
 * color — color is never the only signal (Req 16.4). Its list is labelled
 * "Quest progress" so assistive tech can address it distinctly. It is the only
 * six-stage progress display on the screen (the sidebar is persistent across
 * stages). Built from the shared {@link PixelCard} primitive; styling uses
 * design-token utility classes only.
 */
import type { ReactElement } from "react";

import { PixelCard } from "@/components/PixelCard";

import type { StageStep } from "../lib/stages";

export interface AdventureProgressProps {
  /** The ordered six-stage model with each stage's status. */
  steps: readonly StageStep[];
}

/** Human-readable status label (also announced to screen readers). */
function statusLabel(status: StageStep["status"]): string {
  if (status === "complete") return "Done";
  if (status === "current") return "In progress";
  return "Locked";
}

/** Token-based classes for the step marker, keyed by status. */
function markerClasses(status: StageStep["status"]): string {
  if (status === "current") {
    return "border-accent text-accent";
  }
  if (status === "complete") {
    return "border-primary text-primary";
  }
  return "border-muted text-muted";
}

export function AdventureProgress({
  steps,
}: AdventureProgressProps): ReactElement {
  return (
    <PixelCard title="Your quest">
      <ol className="flex flex-col gap-8" aria-label="Quest progress">
        {steps.map((step) => {
          const isCurrent = step.status === "current";
          return (
            <li
              key={step.stage}
              aria-current={isCurrent ? "step" : undefined}
              className={`flex items-center gap-16 border-2 p-8 ${
                isCurrent ? "border-accent" : "border-muted"
              }`}
            >
              <span
                aria-hidden="true"
                className={`font-display border-2 px-8 py-8 ${markerClasses(
                  step.status,
                )}`}
              >
                {step.status === "complete" ? "✓" : step.step}
              </span>
              <span className="flex flex-col">
                <span
                  className={`font-display ${isCurrent ? "text-accent" : ""}`}
                >
                  {step.title}
                </span>
                <span className="font-body text-muted">{step.blurb}</span>
              </span>
              <span className="font-body ml-auto">
                {statusLabel(step.status)}
              </span>
            </li>
          );
        })}
      </ol>
    </PixelCard>
  );
}

export default AdventureProgress;
