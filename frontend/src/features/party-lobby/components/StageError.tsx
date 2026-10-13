/**
 * StageError — a visible, retryable error for a stage screen.
 *
 * Stage screens read the room live and start AI runs. When either fails, say so (and
 * offer a retry where there is one) instead of leaving the party staring at a spinner
 * as though nothing is wrong. Renders nothing when there is no message.
 */
import { PixelButton } from "@/components/PixelButton";

interface StageErrorProps {
  message: string | null;
  onRetry?: () => void;
}

export function StageError({ message, onRetry }: StageErrorProps) {
  if (message === null) return null;
  return (
    <div className="flex flex-col gap-8" data-testid="stage-error">
      <p role="alert" className="font-body text-alert">
        {message}
      </p>
      {onRetry ? (
        <PixelButton variant="secondary" label="TRY AGAIN" onClick={onRetry} />
      ) : null}
    </div>
  );
}
