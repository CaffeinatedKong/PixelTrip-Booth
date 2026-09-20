/**
 * Supabase client — placeholder (Foundation phase).
 *
 * This module reserves the single location where the frontend's Supabase
 * client integration will live. Per the Supabase ownership split
 * (`supabase-architecture.md`, Requirement 13):
 *
 * - The frontend owns only an **anon-key** oriented client. It reads the
 *   public, browser-safe values `NEXT_PUBLIC_SUPABASE_URL` and
 *   `NEXT_PUBLIC_SUPABASE_ANON_KEY` (conceptually — no client is initialised
 *   here yet).
 * - The frontend **never** holds the Supabase service-role key. That key
 *   belongs exclusively to the backend/service role and must not appear in any
 *   committed or bundled frontend file.
 *
 * In the Foundation this performs **no network calls** and does **no real
 * initialisation** — it exists so that, when real services land, all Supabase
 * access is confined to the service layer (`src/services/*.api.ts`) via this
 * client. UI code (`app/`, `src/features`, `src/components`) must never import
 * this module directly.
 */
import { notImplemented } from "./errors";

/** Public, browser-safe Supabase environment variable names (anon-key only). */
export const SUPABASE_URL_ENV = "NEXT_PUBLIC_SUPABASE_URL";
export const SUPABASE_ANON_KEY_ENV = "NEXT_PUBLIC_SUPABASE_ANON_KEY";

/**
 * Return the frontend Supabase client.
 *
 * Placeholder: throws {@link NotImplementedError} in the Foundation phase. When
 * implemented it will lazily create an anon-key client from the public env
 * values above — and will still never reference the service-role key.
 */
export function getSupabaseClient(): never {
  throw notImplemented("getSupabaseClient");
}
