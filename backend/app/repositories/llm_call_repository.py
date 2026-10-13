"""One row per language-model call, with no prompt or answer text (``llm_calls``).

The shape of each call (operation, model, outcome, latency) is enough to see how often the
fallbacks fire; the text carries party data and is deliberately never stored.
"""

from __future__ import annotations

from app.repositories.base import BaseRepository

_TABLE = "llm_calls"

OUTCOMES = frozenset({"ok", "wrong_shape", "all_models_failed"})


class LlmCallRepository(BaseRepository):
    """Appends LLM call metadata."""

    async def record(
        self, operation: str, model: str | None, outcome: str, latency_ms: int | None
    ) -> None:
        if outcome not in OUTCOMES:
            raise ValueError(f"unknown LLM call outcome {outcome!r}")
        try:
            await (
                self._client.table(_TABLE)
                .insert(
                    {
                        "operation": operation[:80],
                        "model": model,
                        "outcome": outcome,
                        "latency_ms": None if latency_ms is None else max(0, int(latency_ms)),
                    }
                )
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="record", table=_TABLE)
