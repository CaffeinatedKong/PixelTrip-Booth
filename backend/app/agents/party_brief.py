"""The party brief: everyone's saved preferences, summarised for a prompt.

Character creation saves option ids per member. A prompt needs more than a merged
list of them: it needs to know *how many* members want each thing, what each
member wants on their own, the trip length, and a budget it can trust. This
module builds that once, so every prompt describes the party the same way.

Rules that are easy to get wrong:

* ``destinations`` mixes two things. Trip types ("asia", "beach-escape") are
  wishes about the *kind* of trip; anything else is a real place a member typed.
  Only real places can ever become destination cards.
* ``travel_style`` holds the member's group role (leader, planner, ...), not a
  travel style, and is labelled that way.
* The budget level is the lowest tier anyone picked (``appearance.budgetTier``
  on the character). A typed amount is only trusted from
  :data:`MIN_RELIABLE_BUDGET` up; a "2" is a typo, not a plan.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.agents.group_profile import is_region_word
from app.agents.preference_labels import (
    ACTIVITIES,
    BUDGET_TIERS,
    GROUP_ROLES,
    PRIORITIES,
    TRIP_TYPES,
    label_for,
)

#: A typed budget below this (SGD per person) is treated as not stated.
MIN_RELIABLE_BUDGET = 100
#: Every trip departs from here (the frontend fixes the origin).
DEPARTURE_CITY = "Singapore"
CURRENCY = "SGD"
MAX_NAME_CHARS = 40
MAX_PLACE_CHARS = 80


@dataclass
class MemberBrief:
    name: str
    is_leader: bool
    role: str | None
    budget_level: str | None
    trip_types: list[str]
    priorities: list[str]
    activities: list[str]


@dataclass
class PartyBrief:
    party_size: int
    start: str | None
    end: str | None
    days: int | None
    budget_level: str | None
    budget_level_note: str
    budget_amount: float | None
    trip_types: list[tuple[str, int]]
    priorities: list[tuple[str, int]]
    activities: list[tuple[str, int]]
    roles: list[str]
    named_places: list[str]
    members: list[MemberBrief] = field(default_factory=list)

    @property
    def member_names(self) -> list[str]:
        return [m.name for m in self.members]


def build_party_brief(
    members: list[dict[str, Any]],
    preferences: list[dict[str, Any]],
    characters: list[dict[str, Any]] | None,
    availability_overlap: list[dict[str, str]] | None,
) -> PartyBrief:
    """Summarise the party from raw rows (no I/O)."""
    prefs_by_member = {str(p.get("member_id")): p for p in preferences}
    tier_by_member = {
        str(c.get("member_id")): _budget_tier(c) for c in characters or [] if isinstance(c, dict)
    }

    member_briefs: list[MemberBrief] = []
    trip_type_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    activity_counts: Counter[str] = Counter()
    tiers: list[str] = []
    roles: list[str] = []
    named_places: list[str] = []
    amounts: list[float] = []

    for index, member in enumerate(members, start=1):
        member_id = str(member.get("id"))
        prefs = prefs_by_member.get(member_id)
        if prefs is None:
            continue
        name = _clean(member.get("display_name"), MAX_NAME_CHARS) or f"Member {index}"
        trip_types = _unique(
            _trip_type_label(d) for d in _list(prefs.get("destinations")) if is_region_word(str(d))
        )
        for place in _list(prefs.get("destinations")):
            cleaned = _clean(place, MAX_PLACE_CHARS)
            if cleaned and not is_region_word(cleaned):
                if cleaned.lower() not in {p.lower() for p in named_places}:
                    named_places.append(cleaned)
        priorities = _unique(label_for(i, PRIORITIES) for i in _list(prefs.get("interests")))
        activities = _unique(
            label_for(_activity_name(a), ACTIVITIES)
            for a in _list(prefs.get("activities"))
            if _activity_name(a)
        )
        tier = tier_by_member.get(member_id)
        role = label_for(prefs["travel_style"], GROUP_ROLES) if prefs.get("travel_style") else None

        trip_type_counts.update(trip_types)
        priority_counts.update(priorities)
        activity_counts.update(activities)
        if tier:
            tiers.append(tier)
        if role and role not in roles:
            roles.append(role)
        budget = prefs.get("budget")
        if isinstance(budget, int | float) and budget >= MIN_RELIABLE_BUDGET:
            amounts.append(float(budget))

        member_briefs.append(
            MemberBrief(
                name=name,
                is_leader=member.get("role") == "owner" or bool(member.get("is_owner")),
                role=role,
                budget_level=BUDGET_TIERS.get(tier) if tier else None,
                trip_types=trip_types,
                priorities=priorities,
                activities=activities,
            )
        )

    start, end, days = _window(availability_overlap or [])
    budget_level, note = _budget_level(tiers, len(member_briefs))
    return PartyBrief(
        party_size=len(member_briefs),
        start=start,
        end=end,
        days=days,
        budget_level=budget_level,
        budget_level_note=note,
        budget_amount=min(amounts) if amounts else None,
        trip_types=_ranked(trip_type_counts),
        priorities=_ranked(priority_counts),
        activities=_ranked(activity_counts),
        roles=roles,
        named_places=named_places,
        members=member_briefs,
    )


# --- Rendering ------------------------------------------------------------------------


def trip_text(brief: PartyBrief) -> str:
    if brief.start and brief.end and brief.days:
        return (
            f"{brief.days} days, {_pretty(brief.start)} to {_pretty(brief.end)} "
            f"(dates every member can make), departing from {DEPARTURE_CITY}"
        )
    return f"Dates not set yet, departing from {DEPARTURE_CITY}"


def budget_text(brief: PartyBrief) -> str:
    level = (
        f"Budget level: {brief.budget_level.lower()} ({brief.budget_level_note})"
        if brief.budget_level
        else "Budget level: not stated"
    )
    amount = (
        f"Budget per person for the whole trip: {CURRENCY} {brief.budget_amount:,.0f} "
        "(the lowest in the party)"
        if brief.budget_amount is not None
        else "Budget per person: no reliable amount given"
    )
    return f"{level}\n{amount}"


def wants_text(brief: PartyBrief) -> str:
    size = brief.party_size or 1
    shared = [label for label, count in brief.priorities + brief.activities if count > 1]
    solo = [
        f"{m.name}: {label}"
        for m in brief.members
        for label in m.priorities + m.activities
        if dict(brief.priorities + brief.activities).get(label) == 1
    ]

    def counted(items: list[tuple[str, int]]) -> str:
        return ", ".join(f"{label} ({count}/{size})" for label, count in items) or "none chosen"

    return (
        f"- Trip types / regions: {counted(brief.trip_types)}\n"
        f"- Priorities: {counted(brief.priorities)}\n"
        f"- Activities: {counted(brief.activities)}\n"
        f"- Group roles (how each member acts in the group, not a travel style): "
        f"{', '.join(brief.roles) or 'not given'}\n"
        f"- Shared by 2+ members: {', '.join(shared) or 'nothing yet'}\n"
        f"- Only one member asked for: {', '.join(solo) or 'nothing'}"
    )


def members_text(brief: PartyBrief) -> str:
    lines = []
    for member in brief.members:
        parts = [
            "trip types: " + (", ".join(member.trip_types) or "any"),
            "priorities: " + (", ".join(member.priorities) or "any"),
            "activities: " + (", ".join(member.activities) or "any"),
            "budget: " + (member.budget_level or "not stated"),
        ]
        if member.role:
            parts.append(f"role: {member.role}")
        name = f"{member.name} (party leader)" if member.is_leader else member.name
        lines.append(f"- {name}: " + " | ".join(parts))
    return "\n".join(lines) or "- (no member details)"


def named_places_text(brief: PartyBrief) -> str:
    return "\n".join(f"- {place}" for place in brief.named_places) or "- none"


# --- Helpers --------------------------------------------------------------------------


def _trip_type_label(value: Any) -> str:
    """Screen label for a trip type id ("beach-escape"), or the typed region, tidied."""
    key = "".join(ch for ch in str(value).lower() if ch.isalpha())
    for trip_id, label in TRIP_TYPES.items():
        if key == "".join(ch for ch in trip_id if ch.isalpha()):
            return label
    return label_for(str(value).strip(), {})


def _budget_tier(character: dict[str, Any]) -> str | None:
    appearance = character.get("appearance")
    if not isinstance(appearance, dict):
        return None
    tier = str(appearance.get("budgetTier") or "").strip().lower()
    return tier if tier in BUDGET_TIERS else None


def _budget_level(tiers: list[str], size: int) -> tuple[str | None, str]:
    if not tiers:
        return None, ""
    order = list(BUDGET_TIERS)
    lowest = min(tiers, key=order.index)
    count = sum(1 for t in tiers if t == lowest)
    return BUDGET_TIERS[lowest], f"{count} of {size} chose {BUDGET_TIERS[lowest]} Budget"


def _window(overlap: list[dict[str, str]]) -> tuple[str | None, str | None, int | None]:
    """The longest shared date range, and its length in days."""
    best: tuple[str | None, str | None, int | None] = (None, None, None)
    for entry in overlap:
        try:
            start, end = date.fromisoformat(entry["start"]), date.fromisoformat(entry["end"])
        except (KeyError, TypeError, ValueError):
            continue
        days = (end - start).days + 1
        if days > 0 and (best[2] is None or days > best[2]):
            best = (entry["start"], entry["end"], days)
    return best


def _pretty(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%b %Y}"


def _activity_name(activity: Any) -> str:
    if isinstance(activity, dict):
        return str(activity.get("name") or "").strip()
    return str(activity or "").strip()


def _ranked(counts: Counter[str]) -> list[tuple[str, int]]:
    # Counter keeps first-seen order for ties, so members' own order breaks ties.
    return sorted(counts.items(), key=lambda kv: -kv[1])


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean(value: Any, limit: int) -> str | None:
    text = " ".join(str(value or "").split())[:limit].strip()
    return text or None


def _unique(values: Any) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
