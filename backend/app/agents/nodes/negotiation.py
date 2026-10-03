"""Negotiation_Node — REFINE stage itinerary negotiation.

Implemented in task 20. See :mod:`app.agents.nodes.discovery` for why this is a
placeholder rather than an empty stub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.state import AgentState


async def negotiation_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """Negotiate itinerary feedback into a new version for the REFINE stage.

    Raises:
        NotImplementedError: Always, until task 20 implements this node.
    """
    raise NotImplementedError("negotiation_node is implemented in task 20")
