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

    Required fields carry no default; a missing value raises a validation error
    surfaced via :func:`get_settings` as a clear startup ``ConfigError``.

    Secret-bearing fields are declared ``repr=False`` so they are omitted from
    ``repr(settings)`` and any logging that stringifies the settings object.
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

    # --- Supabase (service-role; backend only) ---
    # Required: the backend cannot serve any data operation without these.
    supabase_url: str
    supabase_service_role_key: str = Field(repr=False)

    # --- CORS ---
    frontend_url: str = Field(default="http://localhost:3000")

    # --- Agent layer caps (spec 03, Requirement 12.10) ---
    # Read through Settings rather than embedded as literals in node code.
    iteration_cap: int = Field(default=3, ge=1, le=10)
    tool_call_cap: int = Field(default=10, ge=1, le=50)

    # --- External_Tool configuration (spec 03, Requirement 19.4) ---
    external_tool_timeout_seconds: int = Field(default=10, ge=1, le=60)
    flight_api_url: str = Field(default="")
    flight_api_key: str = Field(default="", repr=False)
    places_api_url: str = Field(default="")
    places_api_key: str = Field(default="", repr=False)
    weather_api_url: str = Field(default="")
    weather_api_key: str = Field(default="", repr=False)

    # --- LLM provider (spec 03) ---
    ai_provider_api_key: str = Field(default="", repr=False)
    llm_model_name: str = Field(default="gemini-3.8-flash", min_length=1)
    #: Comma-separated models tried, in order, when the primary one is unavailable
    #: (free-tier quotas are per model, so a fallback multiplies the daily budget).
    llm_fallback_models: str = Field(default="gemini-3.7-flash,gemini-3.5-flash")
    llm_timeout_seconds: int = Field(default=30, ge=1, le=120)
    llm_max_output_tokens: int = Field(default=8192, ge=1, le=65536)
    #: Gemini Flash models spend output tokens on hidden "thinking" unless told not
    #: to; 0 turns it off (fast, cheap, plenty for these structured tasks). Models
    #: that cannot disable thinking (e.g. Pro) need ``-1`` (dynamic) or a positive
    #: budget instead.
    llm_thinking_budget: int = Field(default=0, ge=-1)

    @field_validator("supabase_url")
    @classmethod
    def _validate_supabase_url(cls, v: str) -> str:
        """Reject a URL missing a scheme or host so misconfiguration fails fast."""
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("SUPABASE_URL must be a valid URL with a scheme and host")
        return v

    @field_validator("supabase_service_role_key")
    @classmethod
    def _validate_service_role_key(cls, v: str) -> str:
        """Reject an empty or whitespace-only service-role key."""
        if not v.strip():
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY must not be empty")
        return v

    @property
    def llm_model_chain(self) -> tuple[str, ...]:
        """The primary model followed by the fallbacks, de-duplicated, in order."""
        chain: list[str] = []
        for name in (self.llm_model_name, *self.llm_fallback_models.split(",")):
            cleaned = name.strip()
            if cleaned and cleaned not in chain:
                chain.append(cleaned)
        return tuple(chain)

    def secret_values(self) -> tuple[str, ...]:
        """Return every configured secret value, for redaction checks.

        Used by the agent layer's log/error redaction helpers and by the test
        suite's secret-non-disclosure assertions (Requirement 20.5, 21.12).
        Empty values are excluded so an unset optional credential never turns
        into a vacuous ``"" in text`` match.
        """
        candidates = (
            self.supabase_service_role_key,
            self.flight_api_key,
            self.places_api_key,
            self.weather_api_key,
            self.ai_provider_api_key,
        )
        return tuple(value for value in candidates if value.strip())


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
