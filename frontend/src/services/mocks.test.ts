/**
 * Mock-shape smoke tests.
 *
 * Assert that representative mock methods return contract-shaped data (the
 * fields named in `api-contracts.md`, the single source of truth) and that the
 * realtime `subscribe` unsubscribe function stops all further callbacks.
 *
 * Kept minimal and non-speculative per the design's Testing Strategy: one
 * representative call per service plus the subscribe/unsubscribe behaviour.
 *
 * Validates: Requirements 7.2, 7.3, 7.4, 9.1
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { MockGuestService } from "./guest.mock";
import { MockRoomService } from "./room.mock";
import { MockChatService } from "./chat.mock";
import { MockVoteService } from "./vote.mock";
import { MockItineraryService } from "./itinerary.mock";

// Fixture ids (mirrors src/mocks). Used to exercise lookups that resolve to
// fixture data rather than null.
const ROOM_ID = "22222222-2222-4222-8222-222222222222";
const GUEST_ID = "11111111-1111-4111-8111-111111111111";
const VOTE_SESSION_ID = "99999999-9999-4999-8999-999999999999";
const TRIP_ID = "bbbbbbb0-bbbb-4bbb-8bbb-bbbbbbbbbbb0";

describe("MockGuestService", () => {
  it("createGuest returns a Guest with a generated id and the given name", async () => {
    const guest = await new MockGuestService().createGuest({
      displayName: "Adventurer",
    });
    expect(typeof guest.id).toBe("string");
    expect(guest.id.length).toBeGreaterThan(0);
    expect(guest.displayName).toBe("Adventurer");
  });

  it("getGuest resolves a contract-shaped Guest for a known id", async () => {
    const guest = await new MockGuestService().getGuest(GUEST_ID);
    expect(guest).not.toBeNull();
    expect(guest).toMatchObject({
      id: expect.any(String),
      displayName: expect.any(String),
    });
  });
});

describe("MockRoomService", () => {
  it("getRoom resolves a contract-shaped PartyRoom for a known id", async () => {
    const room = await new MockRoomService().getRoom(ROOM_ID);
    expect(room).not.toBeNull();
    expect(room).toMatchObject({
      id: ROOM_ID,
      name: expect.any(String),
      ownerId: expect.any(String),
      status: expect.any(String),
      planningStage: expect.any(String),
    });
  });
});

describe("MockChatService", () => {
  it("listMessages returns contract-shaped Message objects for the room", async () => {
    const messages = await new MockChatService().listMessages(ROOM_ID);
    expect(messages.length).toBeGreaterThan(0);
    for (const message of messages) {
      expect(message).toMatchObject({
        id: expect.any(String),
        roomId: ROOM_ID,
        createdAt: expect.any(String),
        senderType: expect.any(String),
        kind: expect.any(String),
      });
      expect(message).toHaveProperty("senderId");
      expect(message).toHaveProperty("content");
    }
  });
});

describe("MockVoteService", () => {
  it("getSession resolves a contract-shaped VoteSession for a known id", async () => {
    const session = await new MockVoteService().getSession(VOTE_SESSION_ID);
    expect(session).not.toBeNull();
    expect(session).toMatchObject({
      voteSessionId: VOTE_SESSION_ID,
      roomId: expect.any(String),
      question: expect.any(String),
      status: expect.any(String),
    });
    expect(Array.isArray(session?.options)).toBe(true);
    for (const option of session?.options ?? []) {
      expect(option).toMatchObject({
        id: expect.any(String),
        label: expect.any(String),
        count: expect.any(Number),
      });
    }
  });
});

describe("MockItineraryService", () => {
  it("getCurrent resolves a contract-shaped ItineraryVersion for a known trip", async () => {
    const version = await new MockItineraryService().getCurrent(TRIP_ID);
    expect(version).not.toBeNull();
    expect(version).toMatchObject({
      version: expect.any(Number),
      source: expect.any(String),
      isCurrent: expect.any(Boolean),
    });
    expect(version?.itinerary).toMatchObject({
      tripId: TRIP_ID,
      roomId: expect.any(String),
      title: expect.any(String),
      summary: expect.any(String),
    });
    expect(Array.isArray(version?.itinerary.days)).toBe(true);
  });
});

describe("MockChatService.subscribe", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("delivers callbacks over time and stops after unsubscribe", () => {
    vi.useFakeTimers();
    const onMessage = vi.fn();
    const chat = new MockChatService();

    const unsubscribe = chat.subscribe(ROOM_ID, onMessage);

    // Advance past one emission interval — a callback should fire.
    vi.advanceTimersByTime(3000);
    expect(onMessage).toHaveBeenCalledTimes(1);

    // Each delivered message is contract-shaped and scoped to the room.
    expect(onMessage.mock.calls[0][0]).toMatchObject({
      id: expect.any(String),
      roomId: ROOM_ID,
      createdAt: expect.any(String),
      senderType: expect.any(String),
      kind: expect.any(String),
    });

    // Unsubscribe, then advance well past several intervals: no more callbacks.
    unsubscribe();
    const callsAfterUnsubscribe = onMessage.mock.calls.length;
    vi.advanceTimersByTime(30000);
    expect(onMessage).toHaveBeenCalledTimes(callsAfterUnsubscribe);
  });
});
