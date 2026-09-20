/**
 * Shared error types for the service layer.
 *
 * `NotImplementedError` is thrown by the Real_Service placeholder
 * implementations (`src/services/*.api.ts`) during the Foundation phase. In
 * `real` mode, every service method fails loudly with this error rather than
 * returning a value or touching Supabase/FastAPI — so integration gaps surface
 * as explicit errors instead of silent failures (per `development-rules.md`).
 *
 * Frontend development should run with `NEXT_PUBLIC_SERVICE_MODE=mock`, where
 * the contract-shaped mock implementations are used instead.
 */

/** Raised when a real (backend-backed) service method is not yet implemented. */
export class NotImplementedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NotImplementedError";
  }
}

/**
 * Build a consistent {@link NotImplementedError} for a real service method.
 *
 * @param member  Fully-qualified method name, e.g. `"GuestService.createGuest"`.
 */
export function notImplemented(member: string): NotImplementedError {
  return new NotImplementedError(
    `${member} is not implemented (real mode). ` +
      `Set NEXT_PUBLIC_SERVICE_MODE=mock during frontend development.`,
  );
}
