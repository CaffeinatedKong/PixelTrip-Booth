"""Booking COM adapter and the flight provider chain (no real requests)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.agents.tools import booking_rapidapi, flights
from app.agents.tools.base import FlightSearchResponse
from app.agents.tools.booking_rapidapi import BookingRapidApiClient, to_flight_options
from app.agents.tools.flights import FlightSearchTool, NoFlightProviderAvailableError
from app.core.config import Settings

pytestmark = pytest.mark.anyio

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "booking_com15_search.json").read_text())
QUERY = {
    "origin": "SIN",
    "destination": "Penang, Malaysia",
    "depart_after": "2026-11-12",
    "depart_before": "2026-11-16",
}


@pytest.fixture(autouse=True)
def fresh_state():
    booking_rapidapi._place_cache.clear()
    flights._unavailable_until.clear()
    yield
    booking_rapidapi._place_cache.clear()
    flights._unavailable_until.clear()


def settings(provider: str = "booking_rapidapi") -> Settings:
    return Settings(
        supabase_url="https://x.supabase.co",
        supabase_service_role_key="k",
        flight_provider=provider,
        flight_api_key="rapid-key",
        flight_currency="SGD",
    )


def booking_transport(requests: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("searchDestination"):
            code = "SIN" if request.url.params["query"] == "SIN" else "PEN"
            return httpx.Response(200, json={"status": True, "data": [{"id": f"{code}.AIRPORT"}]})
        return httpx.Response(200, json=FIXTURE)

    return httpx.MockTransport(handler)


# --- Booking COM adapter --------------------------------------------------------------


def test_offers_map_to_flight_options():
    options = to_flight_options(FIXTURE["data"]["flightOffers"])

    first = options[0]
    assert first == {
        "id": "1_AK1722_2_AK1721.SIN20261112.PEN20261116",
        "carrier": "Air Asia",
        "flight_number": "AK1722",
        "origin": "SIN",
        "destination": "PEN",
        "depart_at": "2026-11-12T13:50:00",
        "arrive_at": "2026-11-12T15:10:00",
        "price": 140.82,
        "duration_minutes": 80,
        "stops": 0,
        "return_depart_at": "2026-11-16T09:55:00",
        "return_arrive_at": "2026-11-16T11:20:00",
    }
    FlightSearchResponse.model_validate({"options": options})  # fits the agent's model


def test_malformed_offers_are_skipped():
    assert to_flight_options([{"segments": []}, {"flightKey": "x"}]) == []


async def test_search_resolves_places_once_and_sends_a_round_trip():
    requests: list[httpx.Request] = []
    client = BookingRapidApiClient(settings(), transport=booking_transport(requests))

    result = await client.search(**QUERY)
    await client.search(**QUERY)  # places come from the cache the second time

    assert len(result["options"]) == 3
    paths = [r.url.path.rsplit("/", 1)[-1] for r in requests]
    assert paths == ["searchDestination", "searchDestination", "searchFlights", "searchFlights"]
    search = requests[2]
    assert search.url.params["fromId"] == "SIN.AIRPORT"
    assert search.url.params["toId"] == "PEN.AIRPORT"
    assert search.url.params["returnDate"] == "2026-11-16"
    assert search.url.params["currency_code"] == "SGD"
    assert search.headers["x-rapidapi-host"] == "booking-com15.p.rapidapi.com"
    assert search.headers["x-rapidapi-key"] == "rapid-key"


# --- Provider chain -------------------------------------------------------------------


class FakeChain(FlightSearchTool):
    """The chain with scripted providers instead of HTTP."""

    def __init__(self, provider: str, answers: dict[str, Any]) -> None:
        super().__init__(settings(provider))
        self.answers = answers
        self.calls: list[str] = []

    async def _search(self, provider: str, **params: Any) -> dict[str, Any]:
        self.calls.append(provider)
        answer = self.answers[provider]
        if isinstance(answer, Exception):
            raise answer
        return answer


def http_error(status: int, headers: dict[str, str] | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(status, headers=headers or {}, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


FLIGHTS = {"options": [{"id": "f1"}]}


async def test_settings_parse_an_ordered_provider_list():
    chain = settings(
        " booking_rapidapi , skyscanner_rapidapi,booking_rapidapi"
    ).flight_provider_chain
    assert chain == ("booking_rapidapi", "skyscanner_rapidapi")
    with pytest.raises(ValueError):
        settings("booking_rapidapi,made_up")


async def test_the_first_provider_that_answers_wins():
    tool = FakeChain("booking_rapidapi,skyscanner_rapidapi", {"booking_rapidapi": FLIGHTS})

    assert await tool._call(**QUERY) == FLIGHTS
    assert tool.calls == ["booking_rapidapi"]


async def test_out_of_quota_falls_back_and_is_skipped_until_reset():
    tool = FakeChain(
        "skyscanner_rapidapi,booking_rapidapi",
        {
            "skyscanner_rapidapi": http_error(429, {"x-ratelimit-requests-reset": "86400"}),
            "booking_rapidapi": FLIGHTS,
        },
    )

    assert await tool._call(**QUERY) == FLIGHTS
    assert await tool._call(**QUERY) == FLIGHTS
    # Sky Scrapper was asked once, then rested; Booking answered both times.
    assert tool.calls == ["skyscanner_rapidapi", "booking_rapidapi", "booking_rapidapi"]


async def test_not_subscribed_and_other_errors_fall_back():
    tool = FakeChain(
        "skyscanner_rapidapi,generic,booking_rapidapi",
        {
            "skyscanner_rapidapi": http_error(403),
            "generic": booking_rapidapi.PlaceNotFoundError("no matching place"),
            "booking_rapidapi": FLIGHTS,
        },
    )

    assert await tool._call(**QUERY) == FLIGHTS
    assert "skyscanner_rapidapi" in flights._unavailable_until
    assert "generic" not in flights._unavailable_until  # a one-off failure, not a rest


async def test_zero_flights_tries_the_next_provider():
    tool = FakeChain(
        "booking_rapidapi,skyscanner_rapidapi",
        {"booking_rapidapi": {"options": []}, "skyscanner_rapidapi": FLIGHTS},
    )

    assert await tool._call(**QUERY) == FLIGHTS


async def test_every_provider_failing_raises_the_last_error():
    tool = FakeChain(
        "booking_rapidapi,skyscanner_rapidapi",
        {"booking_rapidapi": http_error(500), "skyscanner_rapidapi": http_error(502)},
    )

    with pytest.raises(httpx.HTTPStatusError) as caught:
        await tool._call(**QUERY)
    assert caught.value.response.status_code == 502


async def test_all_providers_resting_fails_fast_without_a_request():
    tool = FakeChain("booking_rapidapi", {"booking_rapidapi": FLIGHTS})
    flights._unavailable_until["booking_rapidapi"] = flights._now() + 999

    with pytest.raises(NoFlightProviderAvailableError):
        await tool._call(**QUERY)
    assert tool.calls == []


async def test_each_provider_gets_the_full_timeout():
    tool = FakeChain("booking_rapidapi,skyscanner_rapidapi", {})
    assert tool._call_timeout_seconds() == 2 * tool._settings.external_tool_timeout_seconds
