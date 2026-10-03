"""Shared test setup.

The app reads Supabase settings at import time. Placeholder values are set here so the
test suite never needs (or touches) a real Supabase project or the developer's ``.env``.
"""

import os

import pytest

os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")


@pytest.fixture
def anyio_backend():
    """Run ``@pytest.mark.anyio`` async tests on asyncio only."""
    return "asyncio"
