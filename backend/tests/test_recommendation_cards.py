"""CR-1: recommendation items carry card copy the frontend renders.

Every destination and flight item has a ``description`` and ``meta`` with ``score``
(0-100), ``whyThisFits``, ``tags``, ``tradeOff`` and ``details``. Flights keep their
factual meta keys alongside.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from app.agents.errors import LLMGenerationError
from app.agents.llm import LLMClient
from app.agents.nodes import discovery
from app.agents.nodes.logistics import _build_proposal as build_flight_proposal
from app.agents.proposals import RecommendationItem
from app.agents.tools.base import FlightOption

anyio = pytest.mark.anyio

CARD_KEYS = {"score", "whyThisFits", "tags", "tradeOff", "details"}

PROFILE: dict[str, Any] = {
    "member_count": 2,
    "destinations": ["Phuket, Thailand"],
    "interests": ["beaches", "food"],
    "hard_constraints": ["no casinos"],
    "availability_overlap": [{"start": "2026-12-20", "end": "2026-12-27"}],
    "budget_ceiling": 1500,
}


def insight(name: str, **overrides: Any) -> dict[str, Any]:
    data = {
        "name": name,
        "score": 92,
        "description": "Island beaches and night markets.",
        "why_this_fits": "Matches the party's love of beaches and food.",
        "tags": ["Budget", "Low crowds", "Nightlife"],
        "trade_off": "Monsoon showers are possible.",
        "details": "Late December is dry season with warm seas.",
    }
    data.update(overrides)
    return data


def llm_answering(*insights: dict[str, Any]) -> AsyncMock:
    llm = AsyncMock(spec=LLMClient)
    llm.generate_structured.return_value = discovery._DestinationInsights(
        insights=[discovery._DestinationInsight(**i) for i in insights]
    )
    return llm


# --- Destinations -------------------------------------------------------------------


@anyio
async def test_destination_items_carry_the_llm_card_copy():
    llm = llm_answering(insight("phuket, thailand"), insight("Bali, Indonesia", score=140))
    cards = await discovery._generate_insights(
        ["Phuket, Thailand", "Bali, Indonesia"], PROFILE, llm
    )

    proposal = discovery._build_proposal(["Phuket, Thailand", "Bali, Indonesia"], PROFILE, cards)
    phuket, bali = proposal["items"]

    assert phuket["id"] == "phuket--thailand"
    assert phuket["description"] == "Island beaches and night markets."
    assert phuket["meta"] == {
        "score": 92,
        "whyThisFits": "Matches the party's love of beaches and food.",
        "tags": ["Budget", "Low crowds", "Nightlife"],
        "tradeOff": "Monsoon showers are possible.",
        "details": "Late December is dry season with warm seas.",
    }
    assert bali["meta"]["score"] == 100  # clamped
    for item in proposal["items"]:
        RecommendationItem.model_validate(item)  # contract shape unchanged
    kwargs = llm.generate_structured.await_args.kwargs
    assert kwargs["operation"] == "destination_insights"
    assert "no casinos" in kwargs["user_prompt"]


@anyio
async def test_a_destination_the_model_skipped_gets_fallback_copy():
    cards = await discovery._generate_insights(
        ["Phuket, Thailand", "Lisbon, Portugal"],
        PROFILE,
        llm_answering(insight("Phuket, Thailand")),
    )

    lisbon = discovery._build_proposal(["Lisbon, Portugal"], PROFILE, cards)["items"][0]

    assert set(lisbon["meta"]) == CARD_KEYS
    assert lisbon["meta"]["score"] == discovery.SUGGESTED_SCORE
    assert lisbon["description"]


@anyio
async def test_copy_mentioning_a_hard_constraint_is_replaced():
    """The business guardrail scans item text; forbidden words would sink the proposal."""
    llm = llm_answering(insight("Phuket, Thailand", tags=["Beaches", "Casinos"]))

    cards = await discovery._generate_insights(["Phuket, Thailand"], PROFILE, llm)

    assert cards == {}


@anyio
async def test_no_llm_means_deterministic_fallback_copy():
    failing = AsyncMock(spec=LLMClient)
    failing.generate_structured.side_effect = LLMGenerationError("destination_insights")
    assert await discovery._generate_insights(["Phuket, Thailand"], PROFILE, failing) == {}
    assert await discovery._generate_insights(["Phuket, Thailand"], PROFILE, None) == {}

    wished, suggested = discovery._build_proposal(["Phuket, Thailand", "Kyoto, Japan"], PROFILE)[
        "items"
    ]

    assert set(wished["meta"]) == CARD_KEYS
    assert wished["meta"]["score"] == discovery.WISHLIST_SCORE
    assert wished["meta"]["tags"] == ["Party wish list"]
    assert suggested["meta"]["score"] == discovery.SUGGESTED_SCORE
    assert "2026-12-20 to 2026-12-27" in suggested["meta"]["details"]


# --- Flights ------------------------------------------------------------------------

CHEAP = FlightOption(
    id="f1",
    carrier="Scoot",
    flight_number="TR808",
    origin="SIN",
    destination="NRT",
    depart_at="2026-12-20T01:00:00",
    arrive_at="2026-12-20T09:00:00",
    price=600.0,
    duration_minutes=480,
    stops=1,
)
FAST = CHEAP.model_copy(
    update={
        "id": "f2",
        "carrier": "Singapore Airlines",
        "flight_number": "SQ12",
        "price": 980.0,
        "duration_minutes": 405,
        "stops": 0,
        "return_depart_at": "2026-12-27T10:30:00",
    }
)


def test_flight_items_keep_their_facts_and_add_card_copy():
    proposal = build_flight_proposal([CHEAP, FAST], currency="SGD")
    cheap, fast = proposal["items"]

    # Factual keys the guardrail, itinerary and tiebreak rely on are untouched.
    assert cheap["meta"]["price"] == 600.0 and cheap["meta"]["flight_number"] == "TR808"
    assert CARD_KEYS <= set(cheap["meta"])
    assert cheap["meta"]["tags"] == ["SGD 600", "Scoot", "8h 00m", "1 stop"]
    assert fast["meta"]["tags"] == ["SGD 980", "Singapore Airlines", "6h 45m", "Direct"]
    assert cheap["meta"]["whyThisFits"] == "The cheapest option for the party."
    assert fast["meta"]["whyThisFits"] == "The quickest journey and a direct flight for the party."
    assert fast["meta"]["tradeOff"] == "SGD 380 more than the cheapest option."
    assert cheap["meta"]["tradeOff"] == "1 stop where other options fly with fewer."
    assert "round trip" in fast["meta"]["details"]
    assert "one way" in cheap["meta"]["details"]
    assert cheap["description"] == "SIN to NRT, 1 stop, 8h 00m, SGD 600."
    for item in proposal["items"]:
        RecommendationItem.model_validate(item)


def test_flight_score_is_value_for_money():
    cheap, fast = build_flight_proposal([CHEAP, FAST], currency="SGD")["items"]

    # Cheapest but slowest with a stop: 95 - 15 - 8. Priciest, fastest, direct: 95 - 30.
    assert cheap["meta"]["score"] == 72
    assert fast["meta"]["score"] == 65
    only = build_flight_proposal([FAST], currency="SGD")["items"][0]
    assert only["meta"]["score"] == 95
    assert only["meta"]["tradeOff"] == "Nothing stands out against the other options."
