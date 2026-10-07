"""Derivation of the party's combined travel profile.

The ``Group_Profile`` is computed fresh inside each ``discovery`` run and held
only in agent state — it is never persisted, because ``agent_run_type`` has no
``group_profile`` value and no table models it (Requirement 7.4).

Two derivations carry real product weight:

* **Availability overlap** is a true intersection. A member who supplied no dates
  contributes nothing rather than blocking the party, but a member who *did*
  supply dates genuinely constrains the result (Requirement 7.2).
* **Budget ceiling** is the *lowest* non-NULL per-member budget, so the most
  constrained traveller governs what the party is offered (Requirement 7.3).
  That is an MVP interpretation: ``product.md`` does not settle whether a party
  budget is per-person, pooled, or averaged, and the initial migration records it
  as an open question. Documented in requirements.md Assumption 9.
"""

from __future__ import annotations

from datetime import date
from typing import Any

#: Keys accepted for a date range inside ``travel_preferences.available_dates``.
#: Tolerant of both shapes because the frontend contract and the mock fixtures
#: have historically used either.
_START_KEYS = ("start", "from", "start_date")
_END_KEYS = ("end", "to", "end_date")


def _parse_date(value: Any) -> date | None:
    """Parse an ISO date (or date-time) string, returning ``None`` if unusable."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    # Accept a full timestamp by taking its date part.
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _first_key(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the value of the first present key in ``keys``."""
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _extract_ranges(available_dates: Any) -> list[tuple[date, date]]:
    """Pull well-formed ``(start, end)`` pairs out of a raw jsonb value.

    Malformed or partial entries are skipped rather than raising: a member's
    sloppy input should not abort a run, it should simply not constrain the
    overlap.
    """
    if not isinstance(available_dates, list):
        return []

    ranges: list[tuple[date, date]] = []
    for entry in available_dates:
        if not isinstance(entry, dict):
            continue
        start = _parse_date(_first_key(entry, _START_KEYS))
        end = _parse_date(_first_key(entry, _END_KEYS))
        if start is None or end is None or end < start:
            continue
        ranges.append((start, end))
    return ranges


def _intersect(
    left: list[tuple[date, date]],
    right: list[tuple[date, date]],
) -> list[tuple[date, date]]:
    """Return the pairwise intersection of two sets of date ranges."""
    overlaps: list[tuple[date, date]] = []
    for l_start, l_end in left:
        for r_start, r_end in right:
            start = max(l_start, r_start)
            end = min(l_end, r_end)
            if start <= end:
                overlaps.append((start, end))
    return _merge(overlaps)


def _merge(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Sort and coalesce touching or overlapping ranges."""
    if not ranges:
        return []
    ordered = sorted(ranges)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def compute_availability_overlap(
    preferences: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Return the date ranges every date-supplying member shares.

    Members who supplied no usable range are skipped: they are treated as
    unconstrained rather than as blocking the whole party (Requirement 7.2).

    Returns:
        A list of ``{"start": iso, "end": iso}`` mappings, empty when the
        date-supplying members share nothing.
    """
    per_member = [
        ranges
        for preference in preferences
        if (ranges := _extract_ranges(preference.get("available_dates")))
    ]
    if not per_member:
        return []

    overlap = _merge(per_member[0])
    for ranges in per_member[1:]:
        overlap = _intersect(overlap, ranges)
        if not overlap:
            break

    return [{"start": start.isoformat(), "end": end.isoformat()} for start, end in overlap]


def compute_budget_ceiling(preferences: list[dict[str, Any]]) -> float | None:
    """Return the lowest non-NULL per-member budget, or ``None`` if all are NULL.

    ``None`` means *unconstrained*, and every budget check must treat it that way
    rather than as zero (Requirement 7.3, 12.14).
    """
    budgets: list[float] = []
    for preference in preferences:
        raw = preference.get("budget")
        if raw is None:
            continue
        try:
            budgets.append(float(raw))
        except (TypeError, ValueError):
            continue
    return min(budgets) if budgets else None


def _string_entries(value: Any) -> list[str]:
    """Flatten a jsonb array into trimmed, non-empty strings.

    Handles both a bare string list and a list of objects carrying a ``name``,
    ``label``, or ``title``, since ``interests``/``activities`` entries appear in
    both shapes.
    """
    if not isinstance(value, list):
        return []

    entries: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            entries.append(item.strip())
        elif isinstance(item, dict):
            for key in ("name", "label", "title", "activity"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    entries.append(candidate.strip())
                    break
    return entries


def _union_across(preferences: list[dict[str, Any]], column: str) -> list[str]:
    """Return the de-duplicated union of a jsonb string column, order preserved."""
    seen: dict[str, None] = {}
    for preference in preferences:
        for entry in _string_entries(preference.get(column)):
            seen.setdefault(entry, None)
    return list(seen)


def compute_required_activities(preferences: list[dict[str, Any]]) -> list[str]:
    """Return activities the party marked as required.

    Priority lives inside the ``activities`` jsonb objects rather than in a
    dedicated column (Requirement 12.6), so this reads the per-entry flag.
    An entry is required when it carries ``priority`` of ``"must_have"`` /
    ``"required"``, or a truthy ``required`` key.
    """
    required: dict[str, None] = {}
    for preference in preferences:
        activities = preference.get("activities")
        if not isinstance(activities, list):
            continue
        for item in activities:
            if not isinstance(item, dict):
                continue
            priority = str(item.get("priority", "")).strip().lower()
            is_required = bool(item.get("required")) or priority in {
                "must_have",
                "must-have",
                "required",
            }
            if not is_required:
                continue
            for key in ("name", "label", "title", "activity"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    required.setdefault(candidate.strip(), None)
                    break
    return list(required)


def compute_group_profile(
    members: list[dict[str, Any]],
    preferences: list[dict[str, Any]],
    characters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive the party's combined travel profile.

    Args:
        members: ``room_members`` rows for the party.
        preferences: ``travel_preferences`` rows for those members.
        characters: ``characters`` rows, included for persona context.

    Returns:
        A mapping with ``member_count``, ``availability_overlap``,
        ``budget_ceiling``, ``interests``, ``activities``,
        ``required_activities``, ``travel_styles``, ``hard_constraints``,
        ``destinations``, and ``appearances``.

        A member with a NULL or empty value for a column contributes nothing for
        that column (Requirement 7.2).
    """
    return {
        "member_count": len(members),
        "preference_count": len(preferences),
        "availability_overlap": compute_availability_overlap(preferences),
        "budget_ceiling": compute_budget_ceiling(preferences),
        "interests": _union_across(preferences, "interests"),
        "activities": _union_across(preferences, "activities"),
        "required_activities": compute_required_activities(preferences),
        "travel_styles": sorted(
            {
                str(p["travel_style"]).strip()
                for p in preferences
                if p.get("travel_style") and str(p["travel_style"]).strip()
            }
        ),
        "hard_constraints": _union_across(preferences, "hard_constraints"),
        "destinations": _union_across(preferences, "destinations"),
        "appearances": [c.get("appearance", {}) for c in (characters or []) if isinstance(c, dict)],
    }
