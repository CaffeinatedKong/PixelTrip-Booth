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
from urllib.parse import urlparse

from pydantic import Field, field_validator
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

    # --- Supabase (required: no defaults, so a missing value fails fast) ---
    supabase_url: str = Field(min_length=1)
    # repr=False keeps the key out of str(settings), repr(settings), and logs.
    supabase_service_role_key: str = Field(min_length=1, repr=False)

    # --- CORS ---
    frontend_url: str = Field(default="http://localhost:3000")

    @field_validator("supabase_url")
    @classmethod
    def _validate_supabase_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("SUPABASE_URL must be a valid URL with a scheme and host")
        return value


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
