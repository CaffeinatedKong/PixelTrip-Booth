"""Load the destination guides for a run: Supabase first, the bundled copy as a safety net.

A catalog read happens at most once every few minutes per process (guides change by hand,
rarely), and it can never fail a run: if the table is empty, unreachable or not migrated
yet, the guides shipped with the code (:func:`~app.agents.fallback_catalog.bundled_catalog`)
are used, so the fallback is always there.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.fallback_catalog import GuideCatalog, bundled_catalog
from app.core.ttl_cache import TTLCache

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.state import RepositoryBundle

logger = logging.getLogger(__name__)

#: How long loaded guides are reused. Edits in Supabase show up within this long.
GUIDE_TTL_SECONDS = 300.0

#: A recommendation needs this many places to choose from; below it the catalog is
#: topped up from the bundled guides (names the table does not already have).
MIN_SUGGESTIONS = 5

GUIDE_CACHE: TTLCache[str, list[dict[str, Any]]] = TTLCache(GUIDE_TTL_SECONDS)


async def load_catalog(repos: RepositoryBundle) -> GuideCatalog:
    """The catalog to use for this run. Never raises."""
    repo = getattr(repos, "guide_repo", None)
    if repo is None:
        return bundled_catalog()
    try:
        rows = await GUIDE_CACHE.get_or_load("active", repo.list_active)
        catalog = GuideCatalog.from_rows(rows)
    except Exception as exc:  # the table may be missing, or the database down
        logger.warning(
            "Destination guides unavailable (%s); using the bundled guides", type(exc).__name__
        )
        return bundled_catalog()
    if len(catalog) == 0:
        return bundled_catalog()
    if len(catalog.pool) < MIN_SUGGESTIONS:
        have = {g.name.lower() for g in catalog.guides}
        extra = [g for g in bundled_catalog().guides if g.name.lower() not in have]
        return GuideCatalog([*catalog.guides, *extra])
    return catalog
