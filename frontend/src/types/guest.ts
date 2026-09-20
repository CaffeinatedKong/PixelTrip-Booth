/**
 * Guest identity (no auth).
 *
 * Mirrors the "Guest Identity Flow" contract in `api-contracts.md`:
 * a lightweight, client-generated guest identity — no tokens, passwords,
 * or accounts. `id` is a client-generated UUID string.
 */
export interface Guest {
  id: string;
  displayName: string;
  avatarUrl?: string;
}
