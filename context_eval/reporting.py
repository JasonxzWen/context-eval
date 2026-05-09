from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from context_eval.models import CaseResult

TELEMETRY_STATUS_ORDER = ["collected", "partial", "error", "unavailable"]


def telemetry_stats_by_variant(results: list[CaseResult]) -> list[dict[str, object]]:
    by_variant: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        by_variant[result.variant].append(result)

    return [
        {"variant": variant, **telemetry_summary(items)}
        for variant, items in sorted(by_variant.items())
    ]


def telemetry_summary(items: list[CaseResult]) -> dict[str, object]:
    return {
        "telemetry_statuses": _status_summary(Counter(item.telemetry_status for item in items)),
        "avg_agent_duration_seconds": _mean_available(
            item.agent_duration_seconds for item in items
        ),
        "avg_total_tokens": _mean_available(item.total_tokens for item in items),
        "avg_tool_calls": _mean_available(item.tool_call_count for item in items),
        "common_tool_names": _common_tool_names(items),
    }


def format_optional_int(value: int | None) -> str:
    return "-" if value is None else str(value)


def format_optional_number(value: float | int | None) -> str:
    return "-" if value is None else f"{float(value):.2f}"


def format_status_counts(value: dict[str, int]) -> str:
    return ",".join(f"{status}={count}" for status, count in value.items()) or "-"


def status_counts_map(counts: Counter[str]) -> dict[str, int]:
    ordered: dict[str, int] = {}
    for status in TELEMETRY_STATUS_ORDER:
        if counts[status]:
            ordered[status] = counts[status]
    for status in sorted(counts):
        if status not in ordered and counts[status]:
            ordered[status] = counts[status]
    return ordered


def _mean_available(values) -> float | None:
    available = [value for value in values if value is not None]
    return mean(available) if available else None


def _status_summary(counts: Counter[str]) -> str:
    return format_status_counts(status_counts_map(counts))


def _common_tool_names(items: list[CaseResult]) -> str:
    tool_counts: Counter[str] = Counter()
    for item in items:
        tool_counts.update(item.tool_calls_by_name)
    return ",".join(name for name, _ in tool_counts.most_common(5)) or "-"
