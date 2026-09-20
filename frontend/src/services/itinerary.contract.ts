/**
 * Itinerary service contract.
 *
 * Typed method signatures only — no feature or business logic. Behaviour is
 * supplied solely by the mock (`itinerary.mock.ts`) or real
 * (`itinerary.api.ts`) implementation. Shapes mirror the "Itinerary Format",
 * "Itinerary Versioning", "Feedback & Refinement" and "Export" sections of
 * `api-contracts.md` (the single source of truth). No Supabase/FastAPI types
 * appear in this surface.
 */
import type {
  ExportPayload,
  Feedback,
  FeedbackInput,
  ItineraryVersion,
} from "@/types";

/** Input for {@link ItineraryService.approve}. */
export interface ApproveInput {
  tripId: string;
  version: number;
}

export interface ItineraryService {
  getCurrent(tripId: string): Promise<ItineraryVersion | null>;
  listVersions(tripId: string): Promise<ItineraryVersion[]>;
  submitFeedback(input: FeedbackInput): Promise<Feedback>;
  approve(input: ApproveInput): Promise<void>;
  export(tripId: string): Promise<ExportPayload>;
}
