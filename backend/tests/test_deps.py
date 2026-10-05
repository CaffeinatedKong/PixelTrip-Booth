"""Tests for the dependency-injection providers.

Two things matter here beyond "it returns an object":

* Every provider's annotation must resolve at runtime. Because these modules use
  ``from __future__ import annotations``, FastAPI's ``get_type_hints`` pass at
  startup would raise ``NameError`` on a type only imported under
  ``TYPE_CHECKING`` — so the resolution itself is asserted.
* No provider may construct a Supabase client itself (Requirement 20.1); the
  client always arrives as an injected argument.
"""

from __future__ import annotations

import inspect
import typing

import pytest
from app.api import deps
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.base import BaseRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.itinerary_version_repository import ItineraryVersionRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.selection_repository import SelectionRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.vote_repository import VoteRepository
from app.repositories.vote_session_repository import VoteSessionRepository


class _StubClient:
    """Stands in for an ``AsyncClient``; providers must not inspect it."""


#: ``provider name -> expected repository class``. Every repository the agent
#: layer reads or writes through.
PROVIDERS: dict[str, type[BaseRepository]] = {
    "get_member_repo": MemberRepository,
    "get_profile_repo": ProfileRepository,
    "get_trip_repo": TripRepository,
    "get_room_repo": RoomRepository,
    "get_message_repo": MessageRepository,
    "get_vote_session_repo": VoteSessionRepository,
    "get_vote_repo": VoteRepository,
    "get_selection_repo": SelectionRepository,
    "get_itinerary_version_repo": ItineraryVersionRepository,
    "get_feedback_repo": FeedbackRepository,
    "get_agent_run_repo": AgentRunRepository,
}


def test_every_provider_exists() -> None:
    """Each repository the agent layer needs has a wired provider."""
    assert len(PROVIDERS) == 11
    for name in PROVIDERS:
        assert hasattr(deps, name), f"missing provider {name}"


def test_providers_cover_every_repository_in_the_bundle() -> None:
    """Every ``RepositoryBundle`` repo field has a matching DI provider.

    Catches the drift that actually bites: adding a repo to the bundle and
    forgetting to wire it, which only fails later at request time.
    """
    import dataclasses

    from app.agents.state import RepositoryBundle

    provided = {p.__name__ for p in PROVIDERS.values()}
    for field in dataclasses.fields(RepositoryBundle):
        if not field.name.endswith("_repo"):
            continue
        # Bundle fields abbreviate: `trip_repo` -> `TripRepository`.
        stem = field.name.removesuffix("_repo")
        expected = "".join(part.title() for part in stem.split("_")) + "Repository"
        assert expected in provided, f"{field.name} has no DI provider ({expected})"


@pytest.mark.parametrize(("name", "expected"), PROVIDERS.items())
def test_provider_returns_expected_repository(name: str, expected: type[BaseRepository]) -> None:
    """Each provider builds its repository from the injected client."""
    provider = getattr(deps, name)
    repo = provider(_StubClient())

    assert isinstance(repo, expected)


@pytest.mark.parametrize("name", PROVIDERS)
def test_provider_annotations_resolve_at_runtime(name: str) -> None:
    """Guards the ``from __future__ import annotations`` + TYPE_CHECKING trap.

    FastAPI resolves dependency annotations at startup. A type imported only for
    type checkers would raise ``NameError`` here — and therefore at boot.
    """
    provider = getattr(deps, name)

    hints = typing.get_type_hints(provider, include_extras=True)

    assert "client" in hints
    assert "return" in hints


@pytest.mark.parametrize("name", PROVIDERS)
def test_provider_takes_client_as_an_argument(name: str) -> None:
    """Requirement 20.1: the client is injected, never constructed internally."""
    provider = getattr(deps, name)
    params = list(inspect.signature(provider).parameters)

    assert params == ["client"]


@pytest.mark.parametrize("name", PROVIDERS)
def test_provider_stores_the_injected_client(name: str) -> None:
    """The repository holds exactly the client it was handed."""
    provider = getattr(deps, name)
    client = _StubClient()

    repo = provider(client)

    assert repo._client is client


def test_providers_return_distinct_instances() -> None:
    """Providers are not accidental singletons sharing mutable state."""
    first = deps.get_trip_repo(_StubClient())
    second = deps.get_trip_repo(_StubClient())

    assert first is not second


def test_supabase_client_alias_is_an_annotated_dependency() -> None:
    """The shared alias carries a Depends marker, which is what avoids ruff B008."""
    metadata = getattr(deps.SupabaseClient, "__metadata__", ())

    assert metadata, "SupabaseClient should be Annotated[...] with a Depends marker"
    assert any(type(m).__name__ == "Depends" for m in metadata)


def test_no_provider_calls_the_client_factory_itself() -> None:
    """Only ``get_supabase_client`` may reach the factory.

    Checked structurally rather than by mocking: a repository provider that
    called the factory would bypass DI and make overriding it in tests useless.
    """
    for name in PROVIDERS:
        source = inspect.getsource(getattr(deps, name))
        assert "create_supabase_client" not in source
        assert "acreate_client" not in source
