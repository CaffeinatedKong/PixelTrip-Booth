# Feature: Party Room — Shared multiplayer surface

The party room is the central multiplayer surface where the group makes decisions
together. It is not a numbered stage; instead it hosts the DISCOVER → WRAP stages
in one shared space.

## What this surface does

The room brings together:

- Pixel characters of all members.
- A group chat interface.
- The AI travel guide (NPC) that drives the conversation.
- Current planning progress across stages.
- Decision cards (options, votes, summaries).

Stages DISCOVER, LOGISTICS, BUILD, REFINE, and WRAP play out inside this shared
room; SETUP feeds it by forming the party and collecting preferences.

## Status

Placeholder only. No feature or business logic lives here yet — this folder
reserves the shared party-room surface in the feature-based structure. Data access
will go through `src/services`; shared UI primitives come from `src/components`.
