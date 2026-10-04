"use client";

/**
 * useCharacterDraft — the character-creation screen's single stateful hook.
 *
 * Owns the in-memory {@link CharacterDraft} via a pure {@link useReducer} plus an
 * in-memory `sessionCharacter`. This hook is frontend-only and session-only: it
 * performs NO persistence (no localStorage/sessionStorage/cookies/IndexedDB), no
 * network/fetch, and imports no service. `save()` is the single projection seam —
 * it only sets `sessionCharacter` in React state from the pure
 * {@link toSessionCharacter} projection.
 *
 * The `canSave` and `toSessionCharacter` logic lives in `../lib/draft`; this hook
 * calls those helpers rather than reimplementing them. The reducer is pure and
 * produces new immutable objects (spread, no mutation).
 */
import { useCallback, useMemo, useReducer, useState } from "react";

import { canSave as computeCanSave, toSessionCharacter } from "../lib/draft";
import type {
  ActivityDraft,
  CharacterDraft,
  DateRange,
  SessionCharacter,
} from "../types";

/** The single-select appearance/style slots driven by {@link select}. */
type SelectSlot =
  | "archetype"
  | "outfit"
  | "accessory"
  | "palette"
  | "travelStyle";

/** The multi-select string-set fields driven by {@link toggle}. */
type ToggleField = "interests" | "destinations";

/** An empty availability range; the draft always keeps at least one. */
const EMPTY_DATE_RANGE: DateRange = { start: "", end: "" };

/** The initial, empty draft rendered before any selection is made. */
const INITIAL_DRAFT: CharacterDraft = {
  archetype: null,
  outfit: null,
  accessory: null,
  palette: null,
  travelStyle: null,
  destinations: [],
  interests: [],
  activities: [],
  hardConstraints: [],
  origin: "",
  budgetText: "",
  availableDates: [EMPTY_DATE_RANGE],
};

/** Discriminated reducer actions over the {@link CharacterDraft}. */
type DraftAction =
  | { type: "select"; slot: SelectSlot; id: string }
  | { type: "toggle"; field: ToggleField; id: string }
  | { type: "toggleActivity"; name: string }
  | {
      type: "setActivityPriority";
      name: string;
      priority: ActivityDraft["priority"];
    }
  | { type: "setBudgetText"; text: string }
  | { type: "setOrigin"; text: string }
  | { type: "addConstraint"; text: string }
  | { type: "removeConstraint"; index: number }
  | { type: "setDateRange"; index: number; range: DateRange }
  | { type: "addDateRange" }
  | { type: "removeDateRange"; index: number };

/** Toggle membership of `id` within an immutable string set. */
function toggleStringSet(
  set: readonly string[],
  id: string,
): readonly string[] {
  return set.includes(id)
    ? set.filter((existing) => existing !== id)
    : [...set, id];
}

/**
 * Pure reducer over the {@link CharacterDraft}. Never mutates its input; every
 * branch returns a new object (or the same reference when nothing changes).
 */
function draftReducer(
  state: CharacterDraft,
  action: DraftAction,
): CharacterDraft {
  switch (action.type) {
    case "select":
      // Single-select, last-write-wins.
      return { ...state, [action.slot]: action.id };

    case "toggle":
      // Multi-select add/remove over a string set.
      return {
        ...state,
        [action.field]: toggleStringSet(state[action.field], action.id),
      };

    case "toggleActivity": {
      const exists = state.activities.some((a) => a.name === action.name);
      const activities = exists
        ? state.activities.filter((a) => a.name !== action.name)
        : [...state.activities, { name: action.name, priority: "must_have" as const }];
      return { ...state, activities };
    }

    case "setActivityPriority": {
      if (!state.activities.some((a) => a.name === action.name)) {
        return state;
      }
      return {
        ...state,
        activities: state.activities.map((a) =>
          a.name === action.name ? { ...a, priority: action.priority } : a,
        ),
      };
    }

    case "setBudgetText":
      return { ...state, budgetText: action.text };

    case "setOrigin":
      return { ...state, origin: action.text };

    case "addConstraint":
      return {
        ...state,
        hardConstraints: [...state.hardConstraints, action.text],
      };

    case "removeConstraint":
      return {
        ...state,
        hardConstraints: state.hardConstraints.filter(
          (_, i) => i !== action.index,
        ),
      };

    case "setDateRange":
      return {
        ...state,
        availableDates: state.availableDates.map((range, i) =>
          i === action.index ? action.range : range,
        ),
      };

    case "addDateRange":
      return {
        ...state,
        availableDates: [...state.availableDates, { ...EMPTY_DATE_RANGE }],
      };

    case "removeDateRange":
      // Never drop below a single range.
      if (state.availableDates.length <= 1) {
        return state;
      }
      return {
        ...state,
        availableDates: state.availableDates.filter(
          (_, i) => i !== action.index,
        ),
      };

    default:
      return state;
  }
}

/** The public surface returned by {@link useCharacterDraft}. */
export interface UseCharacterDraft {
  draft: CharacterDraft;
  select: (slot: SelectSlot, id: string) => void;
  toggle: (field: ToggleField, id: string) => void;
  toggleActivity: (name: string) => void;
  setActivityPriority: (
    name: string,
    priority: ActivityDraft["priority"],
  ) => void;
  setBudgetText: (text: string) => void;
  setOrigin: (text: string) => void;
  addConstraint: (text: string) => void;
  removeConstraint: (index: number) => void;
  setDateRange: (index: number, range: DateRange) => void;
  addDateRange: () => void;
  removeDateRange: (index: number) => void;
  canSave: boolean;
  sessionCharacter: SessionCharacter | null;
  save: () => void;
}

/**
 * Manage the in-memory character draft and the session-only saved character.
 *
 * @returns The draft, stable action callbacks, derived `canSave`, the in-memory
 *   `sessionCharacter`, and a `save()` that projects the draft into state only.
 */
export function useCharacterDraft(): UseCharacterDraft {
  const [draft, dispatch] = useReducer(draftReducer, INITIAL_DRAFT);
  const [sessionCharacter, setSessionCharacter] =
    useState<SessionCharacter | null>(null);

  const select = useCallback((slot: SelectSlot, id: string) => {
    dispatch({ type: "select", slot, id });
  }, []);

  const toggle = useCallback((field: ToggleField, id: string) => {
    dispatch({ type: "toggle", field, id });
  }, []);

  const toggleActivity = useCallback((name: string) => {
    dispatch({ type: "toggleActivity", name });
  }, []);

  const setActivityPriority = useCallback(
    (name: string, priority: ActivityDraft["priority"]) => {
      dispatch({ type: "setActivityPriority", name, priority });
    },
    [],
  );

  const setBudgetText = useCallback((text: string) => {
    dispatch({ type: "setBudgetText", text });
  }, []);

  const setOrigin = useCallback((text: string) => {
    dispatch({ type: "setOrigin", text });
  }, []);

  const addConstraint = useCallback((text: string) => {
    dispatch({ type: "addConstraint", text });
  }, []);

  const removeConstraint = useCallback((index: number) => {
    dispatch({ type: "removeConstraint", index });
  }, []);

  const setDateRange = useCallback((index: number, range: DateRange) => {
    dispatch({ type: "setDateRange", index, range });
  }, []);

  const addDateRange = useCallback(() => {
    dispatch({ type: "addDateRange" });
  }, []);

  const removeDateRange = useCallback((index: number) => {
    dispatch({ type: "removeDateRange", index });
  }, []);

  const canSave = useMemo(() => computeCanSave(draft), [draft]);

  const save = useCallback(() => {
    // Session-only projection seam: state write ONLY, never persistence.
    const projected = toSessionCharacter(draft);
    if (projected !== null) {
      setSessionCharacter(projected);
    }
  }, [draft]);

  return {
    draft,
    select,
    toggle,
    toggleActivity,
    setActivityPriority,
    setBudgetText,
    setOrigin,
    addConstraint,
    removeConstraint,
    setDateRange,
    addDateRange,
    removeDateRange,
    canSave,
    sessionCharacter,
    save,
  };
}
