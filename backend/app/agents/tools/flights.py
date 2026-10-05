"""Flight search, backed by the configured flight data provider.

Two providers, chosen by ``Settings.flight_provider``:

* ``generic`` (default): ``GET flight_api_url`` with the query params, returning the
  ``{"options": [...]}`` shape directly. Used by the tests and by any adapter service.
* ``skyscanner_rapidapi``: the Sky Scrapper listing on RapidAPI, translated by
  :mod:`app.agents.tools.skyscanner_rapidapi`.

Either way, validation is left to :class:`~app.agents.tools.base.FlightSearchResponse`
in the base class.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.agents.tools.base import ExternalTool, FlightSearchResponse
from app.agents.tools.skyscanner_rapidapi import SkyscannerRapidApiClient


class FlightSearchTool(ExternalTool):
    """Searches flights between an origin and a destination."""

    name = "flight_search"
    _response_model = FlightSearchResponse

    async def _call(self, **params: Any) -> dict[str, Any]:
        """Call the flight search endpoint.

        Args:
            **params: Forwarded as query parameters. Callers are expected to
                pass at least ``origin``, ``destination``, and the travel date
                bounds; this method does not interpret them.

        Returns:
            The raw JSON response body.
        """
        if self._settings.flight_provider == "skyscanner_rapidapi":
            return await SkyscannerRapidApiClient(self._settings).search(**params)

        timeout = self._settings.external_tool_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                self._settings.flight_api_url,
                params=params,
                headers={"Authorization": f"Bearer {self._settings.flight_api_key}"},
            )
            response.raise_for_status()
            return response.json()
