/**
 * Barrel for mock fixture data.
 *
 * All fixtures are contract-shaped (derived from `api-contracts.md`, the
 * single source of truth) and are consumed ONLY by the mock service
 * implementations in `src/services/*.mock.ts` — never imported by the UI.
 */
export { mockGuest, mockGuestsById } from "./guests";
export { mockRoom, mockRoomMembers, mockRoomsById } from "./rooms";
export { mockMessages, mockRealtimeMessageTemplate } from "./messages";
export { mockVoteSession, mockVoteSessionsById } from "./votes";
export {
  mockItinerary,
  mockCurrentVersion,
  mockItineraryVersions,
  mockCurrentVersionByTripId,
  mockFeedback,
  mockExportPayload,
} from "./itineraries";
