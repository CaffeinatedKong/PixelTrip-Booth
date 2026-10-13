"""Curated guides for common destinations: what the guide says when the LLM cannot.

The LLM is an enhancement, never a dependency (see ``discovery.py`` and
``itinerary.py``). When it is down, out of quota or answers badly, the stages fall
back to a :class:`GuideCatalog` instead of empty placeholder copy:

* **DISCOVER** offers the catalog's suggestable places, each with real card copy, a
  rough daily cost and a typical trip length, so the vote still has something to compare.
* **BUILD** plans every day the model did not draft from the destination's activity
  bank (:func:`fallback_days`), ranked by the party's own words, with hard constraints
  and the money left for activities respected. A destination with no guide gets a
  generic, honest day shape (arrive, explore, eat, depart) rather than "free time".

**Where the data lives.** In Supabase (``destination_guides`` and
``destination_activities``), so a destination can be added or corrected without a deploy;
:class:`~app.repositories.guide_repository.GuideRepository` loads it. The file
``app/agents/data/destination_guides.json`` is the *same* data in its authored form: the
source the seed migration is generated from (``scripts/export_guides_seed.py``) and the
safety net used when the table is empty or unreachable (:func:`bundled_catalog`), so the
fallback itself can never be missing.

Everything here is static and party-neutral on purpose. Caching a previous party's LLM
answer for reuse would leak their member names and date-specific advice into another
party's trip, so nothing LLM-written is stored here: the guides are written by hand.
Costs are rough SGD per person, the same unit the LLM is asked for, and only ever shown
as estimates.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from app.agents.proposals import ItineraryItemModel

Slot = Literal["morning", "afternoon", "evening"]
SLOTS: tuple[Slot, ...] = ("morning", "afternoon", "evening")

#: Default start time per slot when an activity does not name its own.
SLOT_TIMES: dict[Slot, str] = {"morning": "09:30", "afternoon": "14:00", "evening": "19:00"}

BUNDLED_PATH = Path(__file__).parent / "data" / "destination_guides.json"


@dataclass(frozen=True)
class Activity:
    """One bankable activity: a real, well-known thing to do at the destination."""

    title: str
    slot: Slot
    description: str
    location: str
    cost_sgd: float
    tags: frozenset[str] = frozenset()
    time: str | None = None


@dataclass(frozen=True)
class DestinationGuide:
    """Hand-written guide copy and activity bank for one destination."""

    name: str
    keywords: frozenset[str]
    description: str
    details: str
    tags: tuple[str, ...]
    daily_cost_sgd: int
    typical_days: int
    activities: tuple[Activity, ...] = field(default=())
    #: Offered as a DISCOVER suggestion. ``False`` = itinerary help only, for places
    #: parties often name themselves.
    suggest: bool = True


def _a(
    title: str,
    slot: Slot,
    description: str,
    location: str,
    cost: float,
    *tags: str,
    time: str | None = None,
) -> Activity:
    """Shorthand for the generic, place-agnostic activities below."""
    return Activity(title, slot, description, location, cost, frozenset(tags), time)


def _activity(raw: dict[str, Any]) -> Activity | None:
    slot = raw.get("slot")
    if slot not in SLOTS or not raw.get("title"):
        return None
    return Activity(
        title=str(raw["title"]),
        slot=slot,
        description=str(raw.get("description") or ""),
        location=str(raw.get("location") or ""),
        cost_sgd=float(raw.get("cost_sgd") or 0),
        tags=frozenset(str(t).lower() for t in raw.get("tags") or []),
        time=raw.get("start_time") or raw.get("time") or None,
    )


def guide_from_row(raw: dict[str, Any]) -> DestinationGuide | None:
    """One guide from a Supabase row (or a JSON entry); ``None`` if it is unusable.

    Accepts the activities under ``activities`` (the JSON file) or
    ``destination_activities`` (a Supabase embedded select, ordered by ``sort_order``).
    """
    name = " ".join(str(raw.get("name") or "").split())
    description = str(raw.get("description") or "").strip()
    if not name or not description:
        return None
    activities = raw.get("activities")
    if activities is None:
        activities = sorted(
            raw.get("destination_activities") or [], key=lambda a: a.get("sort_order") or 0
        )
    cost = raw.get("daily_cost_sgd")
    days = raw.get("typical_days")
    return DestinationGuide(
        name=name,
        keywords=frozenset(str(k).lower() for k in raw.get("keywords") or []),
        description=description,
        details=str(raw.get("details") or description),
        tags=tuple(str(t) for t in raw.get("tags") or []),
        daily_cost_sgd=int(cost) if isinstance(cost, int | float) and cost > 0 else 0,
        typical_days=int(days) if isinstance(days, int | float) and days > 0 else 0,
        activities=tuple(a for a in map(_activity, activities) if a is not None),
        suggest=bool(raw.get("suggest", True)),
    )


class GuideCatalog:
    """A set of guides with lookup by name and the DISCOVER fallback pool."""

    def __init__(self, guides: Iterable[DestinationGuide]) -> None:
        self.guides: tuple[DestinationGuide, ...] = tuple(guides)
        self._by_name = {g.name.lower(): g for g in self.guides}
        self._by_city = {g.name.split(",", 1)[0].strip().lower(): g for g in self.guides}

    @classmethod
    def from_rows(cls, rows: Iterable[dict[str, Any]]) -> GuideCatalog:
        return cls(g for g in map(guide_from_row, rows) if g is not None)

    @property
    def pool(self) -> tuple[tuple[str, frozenset[str]], ...]:
        """DISCOVER's region-aware safety net: ``(name, keywords)`` per suggestable guide."""
        return tuple((g.name, g.keywords) for g in self.guides if g.suggest)

    def lookup(self, name: str | None) -> DestinationGuide | None:
        """The guide for ``name`` ("City, Country" or just the city), or ``None``."""
        if not name:
            return None
        key = " ".join(str(name).split()).lower().strip(" .,")
        return self._by_name.get(key) or self._by_city.get(key.split(",", 1)[0].strip())

    def __len__(self) -> int:
        return len(self.guides)


@lru_cache(maxsize=1)
def bundled_catalog() -> GuideCatalog:
    """The catalog shipped with the code: the seed data and the last-resort fallback."""
    data = json.loads(BUNDLED_PATH.read_text(encoding="utf-8"))
    return GuideCatalog.from_rows(data["guides"])


#: The bundled pool, for callers and tests that do not have a loaded catalog.
FALLBACK_POOL = bundled_catalog().pool


def lookup(name: str | None) -> DestinationGuide | None:
    """:meth:`GuideCatalog.lookup` on the bundled catalog."""
    return bundled_catalog().lookup(name)


# --- Fallback day plans ---------------------------------------------------------------


def _generic(city: str) -> dict[Slot, list[Activity]]:
    """Honest, place-agnostic activities for a destination with no guide."""
    return {
        "morning": [
            _a(
                f"Explore central {city}",
                "morning",
                "Walk the main sights and get your bearings.",
                f"{city} centre",
                0,
            ),
            _a(
                "Visit a local market",
                "morning",
                "Browse the stalls and try a local breakfast.",
                city,
                10,
                "food",
                "shopping",
            ),
            _a(
                "Slow morning at a local café",
                "morning",
                "Coffee and a late breakfast somewhere new.",
                city,
                10,
                "food",
                "relaxed",
            ),
        ],
        "afternoon": [
            _a(
                "Top museum or landmark",
                "afternoon",
                "Pick the sight the party most wants to see.",
                city,
                0,
                "culture",
                "history",
            ),
            _a(
                "Neighbourhood wander",
                "afternoon",
                "Explore a different neighbourhood on foot.",
                city,
                0,
                "city",
            ),
            _a(
                "Park or viewpoint",
                "afternoon",
                "Unwind outdoors with a view over the city.",
                city,
                0,
                "nature",
                "relaxed",
            ),
        ],
        "evening": [
            _a(
                "Dinner at a local favourite",
                "evening",
                "Try the dishes the place is known for.",
                city,
                30,
                "food",
            ),
            _a(
                "Evening stroll and dessert",
                "evening",
                "Wander as the lights come on.",
                city,
                10,
                "city",
            ),
            _a(
                "Sunset walk",
                "evening",
                "A free walk to catch the sunset and the evening buzz.",
                city,
                0,
                "city",
                "relaxed",
            ),
        ],
    }


def _arrival_item(city: str) -> Activity:
    return _a(
        "Arrive and check in",
        "afternoon",
        f"Settle in and drop your bags in {city}.",
        city,
        0,
        time="15:00",
    )


def _departure_item(city: str) -> Activity:
    return _a(
        "Pack up and head to the airport",
        "afternoon",
        "Leave plenty of time for the trip back.",
        city,
        0,
        time="12:00",
    )


def _rank(activities: list[Activity], words: set[str]) -> list[Activity]:
    """Best match for the party's own words first; ties keep the guide's order."""
    return [
        a for _i, a in sorted(enumerate(activities), key=lambda p: (-len(p[1].tags & words), p[0]))
    ]


def fallback_days(
    destination: str,
    day_count: int,
    *,
    words: set[str],
    allowed: Callable[[str], bool],
    ceiling: float | None,
    skip_days: set[int] | frozenset[int] = frozenset(),
    catalog: GuideCatalog | None = None,
) -> dict[int, list[ItineraryItemModel]]:
    """Plan every day not in ``skip_days`` from the destination's guide.

    Args:
        destination: The locked destination's name.
        day_count: Total days in the trip.
        words: Lower-cased words the party used (interests, activities, styles).
        allowed: ``allowed(text) -> bool``; ``False`` drops an activity that names
            something a hard constraint forbids.
        ceiling: Money left per person for paid activities, or ``None`` for no
            check. A paid activity that would push the running total over it is
            skipped for a free one.
        skip_days: Days already planned (by the model); they are left out and
            their activities are not reused here.
        catalog: Where to find the destination's guide (the bundled one by default).

    Returns:
        Validated items by day number, ids ``d{day}-i{n}`` as the LLM path uses.
    """
    guide = (catalog or bundled_catalog()).lookup(destination)
    city = (guide.name if guide else destination).split(",", 1)[0].strip() or "the city"
    bank = list(guide.activities) if guide else []
    generic = _generic(city)
    pools: dict[Slot, list[Activity]] = {
        slot: _rank([a for a in bank if a.slot == slot], words) + generic[slot]
        for slot in ("morning", "afternoon", "evening")
    }
    spent = 0.0
    used: dict[str, int] = {}

    def fits(activity: Activity) -> bool:
        text = f"{activity.title} {activity.description} {activity.location}"
        over = ceiling is not None and activity.cost_sgd and spent + activity.cost_sgd > ceiling
        return allowed(text) and not over

    def take(slot: Slot, *, light: bool = False) -> Activity | None:
        """The best unused option for ``slot``; once all are used, the least-used generic.

        ``light`` (departure morning) only draws on the generic options.
        """
        nonlocal spent
        options = generic[slot] if light else pools[slot]
        fresh = [a for a in options if a.title not in used and fits(a)]
        repeats = sorted((a for a in generic[slot] if fits(a)), key=lambda a: used.get(a.title, 0))
        choice = (fresh or repeats or [None])[0]
        if choice is not None:
            used[choice.title] = used.get(choice.title, 0) + 1
            spent += choice.cost_sgd
        return choice

    plan: dict[int, list[ItineraryItemModel]] = {}
    for day in range(1, day_count + 1):
        if day in skip_days:
            continue
        if day_count == 1:
            shape: list[Activity | None] = [take("morning"), take("afternoon"), take("evening")]
        elif day == 1:
            shape = [_arrival_item(city), take("evening")]
        elif day == day_count:
            shape = [take("morning", light=True), _departure_item(city)]
        else:
            shape = [take("morning"), take("afternoon"), take("evening")]
        items = [
            ItineraryItemModel(
                id=f"d{day}-i{n}",
                title=a.title,
                time=a.time or SLOT_TIMES[a.slot],
                description=a.description,
                location=a.location,
                cost=float(a.cost_sgd) if a.cost_sgd else 0.0,
            )
            for n, a in enumerate((a for a in shape if a is not None), start=1)
        ]
        if items:
            plan[day] = items
    return plan
