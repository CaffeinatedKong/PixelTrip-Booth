/**
 * FastAPI client — placeholder (Foundation phase).
 *
 * This module reserves the single location where the frontend's HTTP client
 * for the FastAPI backend will live. It reads the public base URL
 * `NEXT_PUBLIC_API_BASE_URL` (conceptually — no client is created here yet).
 *
 * In the Foundation this performs **no real fetch / network calls** — it exists
 * so that, when real services land, all FastAPI access is confined to the
 * service layer (`src/services/*.api.ts`) via this client. UI code (`app/`,
 * `src/features`, `src/components`) must never import this module directly.
 */
import { notImplemented } from "./errors";

/** Public base URL for the FastAPI backend. */
export const API_BASE_URL_ENV = "NEXT_PUBLIC_API_BASE_URL";

/**
 * Return the FastAPI HTTP client.
 *
 * Placeholder: throws {@link NotImplementedError} in the Foundation phase. When
 * implemented it will return a thin fetch wrapper bound to the base URL above.
 */
export function getApiClient(): never {
  throw notImplemented("getApiClient");
}
