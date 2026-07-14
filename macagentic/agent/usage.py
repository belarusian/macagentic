from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class UsageSnapshot:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class UsageAccumulator:
    """Thread-safe cumulative model usage for one conversation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._totals = UsageSnapshot()

    def add_response(self, response: dict) -> UsageSnapshot | None:
        usage = response.get("usage")
        extra = response.get("extra") or {}
        if not isinstance(usage, dict) and "cost" not in extra:
            return None

        usage = usage if isinstance(usage, dict) else {}
        input_details = usage.get("input_tokens_details") or {}
        if not isinstance(input_details, dict):
            input_details = {}

        increment = UsageSnapshot(
            input_tokens=_integer(usage.get("input_tokens")),
            cached_input_tokens=_integer(
                input_details.get("cached_tokens")
            ),
            cache_write_tokens=_integer(
                input_details.get("cache_write_tokens")
            ),
            output_tokens=_integer(usage.get("output_tokens")),
            cost=_number(extra.get("cost")),
        )
        with self._lock:
            current = self._totals
            self._totals = UsageSnapshot(
                input_tokens=current.input_tokens + increment.input_tokens,
                cached_input_tokens=(
                    current.cached_input_tokens
                    + increment.cached_input_tokens
                ),
                cache_write_tokens=(
                    current.cache_write_tokens
                    + increment.cache_write_tokens
                ),
                output_tokens=current.output_tokens + increment.output_tokens,
                cost=current.cost + increment.cost,
            )
            return self._totals

    def snapshot(self) -> UsageSnapshot:
        with self._lock:
            return self._totals


def display_model_name(model_name: str) -> str:
    for prefix in ("openai/responses/", "openai/"):
        if model_name.startswith(prefix):
            return model_name.removeprefix(prefix)
    return model_name


def format_usage(snapshot: UsageSnapshot, *, color: bool = False) -> str:
    fields = (
        ("Input", f"{snapshot.input_tokens:,}"),
        ("Cached", f"{snapshot.cached_input_tokens:,}"),
        ("Writes", f"{snapshot.cache_write_tokens:,}"),
        ("Output", f"{snapshot.output_tokens:,}"),
    )
    if not color:
        token_text = "  ".join(
            f"{label}: {value}" for label, value in fields
        )
        return f"Usage  {token_text}  Cost: ${snapshot.cost:.2f}"

    dim = "\033[2m"
    cyan = "\033[36m"
    green = "\033[32m"
    reset = "\033[0m"
    token_text = "  ".join(
        f"{dim}{label}:{reset} {cyan}{value}{reset}"
        for label, value in fields
    )
    return (
        f"{dim}Usage{reset}  {token_text}  "
        f"{dim}Cost:{reset} {green}${snapshot.cost:.2f}{reset}"
    )


def print_usage(
    snapshot: UsageSnapshot,
    *,
    stream: TextIO | None = None,
) -> None:
    if stream is None:
        import sys

        stream = sys.stdout
    color = bool(
        getattr(stream, "isatty", lambda: False)()
        and "NO_COLOR" not in os.environ
    )
    print(format_usage(snapshot, color=color), file=stream, flush=True)


def _integer(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _number(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
