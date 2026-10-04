"use client";

/**
 * StageStepper — the six-stage pipeline progress indicator.
 *
 * A simple stepper built from the shared {@link PixelCard} primitive (no new
 * primitive is forked). Shows every stage in order and marks each complete /
 * current / upcoming from the derived {@link StageStep} model. Purely
 * presentational: it takes the step model via props and renders no live data.
 */
import type { ReactElement } from "react";

import { PixelCard } from "@/components/PixelCard";

import type { StageStep } from "../lib/stages";

export interface StageStepperProps {
  /** The ordered stage model with each stage's status. */
  steps: StageStep[];
}

/** Human-readable label for a stage status (also used for the screen reader). */
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

export function StageStepper({ steps }: StageStepperProps): ReactElement {
  return (
    <PixelCard title="Your quest">
      <ol className="flex flex-col gap-8" aria-label="Planning stages">
        {steps.map((step) => (
          <li
            key={step.stage}
            aria-current={step.status === "current" ? "step" : undefined}
            className={`flex items-center gap-16 border-2 p-8 ${
              step.status === "current" ? "border-accent" : "border-muted"
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
              <span className="font-display">{step.title}</span>
              <span className="font-body text-muted">{step.blurb}</span>
            </span>
            <span className="font-body ml-auto">{statusLabel(step.status)}</span>
          </li>
        ))}
      </ol>
    </PixelCard>
  );
}

export default StageStepper;
