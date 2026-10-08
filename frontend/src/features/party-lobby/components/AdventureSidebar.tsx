"use client";

/**
 * AdventureSidebar — the persistent "YOUR ADVENTURE" right-panel host.
 *
 * Composes the sidebar panels in order: party panel, destination + flight
 * placeholders, budget (shown as not-yet-set until confirmed), and the six-stage
 * quest progress. (Trip header + dates are omitted until the trip is confirmed.)
 * Presentational only: the view model arrives via `adventure` and the optional
 * `roomSession` prop supplies the live room code and planning stage. It performs
 * NO data fetching and imports NO concrete service — the room code is read solely
 * from the `roomSession` prop passed in, and `onInvite` is a local no-op.
 *
 * Responsive behaviour (Req 17.2, 17.4, 17.5):
 * - Desktop (>= `lg` breakpoint): a fixed right column whose content is always
 *   visible regardless of the mobile drawer state.
 * - Mobile (< `lg`): a collapsible drawer driven by `useAdventureDrawer`, toggled
 *   by a button that exposes `aria-expanded` and controls the content visibility.
 *
 * Heading "YOUR ADVENTURE" (Req 1.4). Styling uses design-token utility classes
 * only — never raw hex or arbitrary values (Req 19.4).
 */
import type { ReactElement } from "react";

import type { RoomSession } from "@/types/room";

import type { AdventureView } from "../types";
import { useAdventureDrawer } from "../hooks/useAdventureDrawer";
import { buildStageSteps } from "../lib/stages";
import { SidebarPartyPanel } from "./SidebarPartyPanel";
import { SidebarPlaceholderPanel } from "./SidebarPlaceholderPanel";
import { BudgetPanel } from "./BudgetPanel";
import { AdventureProgress } from "./AdventureProgress";

export interface AdventureSidebarProps {
  /** The derived adventure sidebar view model. */
  adventure: AdventureView;
  /** The active room session, or null when no session is available. */
  roomSession?: RoomSession | null;
}

export function AdventureSidebar({
  adventure,
  roomSession,
}: AdventureSidebarProps): ReactElement {
  const drawer = useAdventureDrawer();

  const roomCode = roomSession?.room.roomCode ?? null;
  const stage = roomSession?.room.planningStage ?? "setup";
  const steps = buildStageSteps(stage);

  /** Invite affordance — purely local, performs NO network request (Req 13.4). */
  const handleInvite = (): void => {
    // Intentionally a no-op: inviting is not wired to any service in this feature.
  };

  const contentId = "adventure-sidebar-content";

  return (
    <aside
      aria-label="Your adventure"
      className="flex flex-col gap-16 lg:sticky lg:top-16 lg:self-start"
    >
      <div className="flex items-center justify-between gap-16">
        <h2 className="font-display text-accent">YOUR ADVENTURE</h2>
        {/* Mobile-only drawer toggle; hidden from the desktop fixed column. */}
        <button
          type="button"
          onClick={drawer.toggle}
          aria-expanded={drawer.isOpen}
          aria-controls={contentId}
          className="font-display border-2 border-ink px-16 py-8 lg:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          {drawer.isOpen ? "Hide" : "Show"}
        </button>
      </div>

      {/*
        Desktop (lg+): always shown. Mobile (< lg): visible only while the drawer
        is open. `lg:flex` re-shows the content on desktop regardless of drawer
        state, so the fixed column is always visible there.
      */}
      <div
        id={contentId}
        className={`flex-col gap-16 lg:flex ${drawer.isOpen ? "flex" : "hidden"}`}
      >
        <SidebarPartyPanel
          members={adventure.members}
          capacity={adventure.capacity}
          roomCode={roomCode}
          onInvite={handleInvite}
        />
        <SidebarPlaceholderPanel title="DESTINATION" emptyLabel="Not selected" />
        <SidebarPlaceholderPanel title="FLIGHT" emptyLabel="Not selected" />
        <BudgetPanel />
        <AdventureProgress steps={steps} />
      </div>
    </aside>
  );
}

export default AdventureSidebar;
