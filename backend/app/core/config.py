"""Application settings loaded from the environment.

Settings are read from environment variables (and an optional local ``.env``
file). Required-but-missing values fail fast at startup with a clear error so a
misconfigured backend never boots into a half-configured state.

Foundation phase note: this is scaffolding. Fields here are placeholders that
later features (Supabase service-role access, external APIs) will build on. No
LangGraph/AI configuration is included by design.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid at startup."""


class Settings(BaseSettings):
    """Environment-driven application settings.

    Add required fields (no default) as real integrations land; a missing
    required value will raise a validation error surfaced via
    :func:`get_settings` as a clear startup ``ConfigError``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application metadata (safe defaults; not secret) ---
    app_name: str = Field(default="PixelArt Trip Planner API")
    environment: str = Field(default="development")

    # NOTE: Required-but-missing secrets (e.g. a Supabase service-role key) will
    # be declared here without a default as real backend features land, e.g.:
    #     supabase_service_key: str
    # A missing value then fails fast through get_settings() below.


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings.

    Raises:
        ConfigError: If any required environment value is missing or invalid.
            The message names the offending field(s) so the fix is obvious.
    """
    try:
        return Settings()
    except Exception as exc:  # pydantic ValidationError or similar
        raise ConfigError(
            "Invalid or missing backend configuration. Check your environment "
            f"variables / .env against .env.example. Details: {exc}"
        ) from exc
