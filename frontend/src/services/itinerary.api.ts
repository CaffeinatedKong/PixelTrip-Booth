/**
 * Itinerary service — real (backend-backed) implementation.
 *
 * Placeholder for the Foundation phase: every method throws
 * {@link NotImplementedError} and performs no Supabase/FastAPI access. It holds
 * the shape of the real integration without implementing it, so all backend
 * access stays confined to the service layer. Behaviour arrives when the
 * backend endpoints land; until then run with `NEXT_PUBLIC_SERVICE_MODE=mock`.
 */
import type {
  ExportPayload,
  Feedback,
  FeedbackInput,
  ItineraryVersion,
} from "@/types";
import { notImplemented } from "@/lib/errors";
import type { ApproveInput, ItineraryService } from "./itinerary.contract";

class ItineraryApiService implements ItineraryService {
  getCurrent(_tripId: string): Promise<ItineraryVersion | null> {
    throw notImplemented("ItineraryService.getCurrent");
  }

  listVersions(_tripId: string): Promise<ItineraryVersion[]> {
    throw notImplemented("ItineraryService.listVersions");
  }

  submitFeedback(_input: FeedbackInput): Promise<Feedback> {
    throw notImplemented("ItineraryService.submitFeedback");
  }

  approve(_input: ApproveInput): Promise<void> {
    throw notImplemented("ItineraryService.approve");
  }

  export(_tripId: string): Promise<ExportPayload> {
    throw notImplemented("ItineraryService.export");
  }
}

/** Singleton real Itinerary service placeholder. */
export const itineraryApiService: ItineraryService = new ItineraryApiService();
