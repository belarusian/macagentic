from io import StringIO

from macagentic.agent.usage import (
    UsageAccumulator,
    UsageSnapshot,
    format_usage,
    print_usage,
)


class TTYBuffer(StringIO):
    def isatty(self) -> bool:
        return True


def test_usage_accumulates_all_response_counters_and_cost() -> None:
    usage = UsageAccumulator()

    usage.add_response(
        {
            "usage": {
                "input_tokens": 1200,
                "input_tokens_details": {
                    "cached_tokens": 800,
                    "cache_write_tokens": 300,
                },
                "output_tokens": 100,
            },
            "extra": {"cost": 0.4},
        }
    )
    snapshot = usage.add_response(
        {
            "usage": {
                "input_tokens": 200,
                "input_tokens_details": {"cached_tokens": 100},
                "output_tokens": 50,
            },
            "extra": {"cost": 0.25},
        }
    )

    assert snapshot == UsageSnapshot(
        input_tokens=1400,
        cached_input_tokens=900,
        cache_write_tokens=300,
        output_tokens=150,
        cost=0.65,
    )


def test_usage_plain_text_format_is_exact() -> None:
    snapshot = UsageSnapshot(
        input_tokens=12345,
        cached_input_tokens=8192,
        cache_write_tokens=4096,
        output_tokens=1024,
        cost=0.65,
    )

    assert format_usage(snapshot) == (
        "Usage  Input: 12,345  Cached: 8,192  Writes: 4,096  "
        "Output: 1,024  Cost: $0.65"
    )


def test_usage_print_uses_tty_color_and_honors_no_color(
    monkeypatch,
) -> None:
    snapshot = UsageSnapshot(input_tokens=1, cost=0.01)
    stream = TTYBuffer()
    monkeypatch.delenv("NO_COLOR", raising=False)

    print_usage(snapshot, stream=stream)

    assert "\033[36m1\033[0m" in stream.getvalue()

    stream = TTYBuffer()
    monkeypatch.setenv("NO_COLOR", "1")
    print_usage(snapshot, stream=stream)

    assert "\033[" not in stream.getvalue()
