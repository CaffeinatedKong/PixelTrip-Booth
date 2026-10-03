"""Flight search, backed by the configured flight data provider.

The provider itself is unspecified by the contracts — ``Settings.flight_api_url``
points at whatever Dev C wires up for the deployment. This client only owns the
HTTP shape (query params in, JSON out) and leaves validation to
:class:`~app.agents.tools.base.FlightSearchResponse` in the base class.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.agents.tools.base import ExternalTool, FlightSearchResponse


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
        timeout = self._settings.external_tool_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                self._settings.flight_api_url,
                params=params,
                headers={"Authorization": f"Bearer {self._settings.flight_api_key}"},
            )
            response.raise_for_status()
            return response.json()
