from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from context_eval.models import CaseResult

RUN_STATUS_ORDER = [
    "completed",
    "validation_failed",
    "agent_failed",
    "timeout",
    "overlay_failed",
    "workspace_failed",
    "internal_error",
]
VALIDATION_STATUS_ORDER = ["passed", "failed", "skipped"]
CONFIDENCE_ORDER = ["high", "medium", "low"]
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
        "avg_command_calls": _mean_available(item.command_call_count for item in items),
        "common_tool_names": _common_tool_names(items),
    }


def run_matrix_overview(results: list[CaseResult]) -> dict[str, int]:
    return {
        "task_count": len({result.task_id for result in results}),
        "variant_count": len({result.variant for result in results}),
        "agent_count": len({result.agent_name for result in results}),
        "trial_count": len({result.trial_index for result in results}),
        "case_count": len(results),
        "failed_count": sum(1 for result in results if is_failed_result(result)),
        "timeout_count": sum(1 for result in results if is_timeout_result(result)),
        "low_confidence_count": sum(1 for result in results if result.confidence == "low"),
        "telemetry_gap_count": sum(1 for result in results if has_telemetry_gap(result)),
        "hard_evaluation_failed_count": sum(
            1 for result in results if result.hard_evaluation_status == "failed"
        ),
        "soft_evaluation_payload_count": sum(
            1 for result in results if result.soft_evaluation_status == "payload_generated"
        ),
    }


def format_matrix_overview_inline(overview: dict[str, int]) -> str:
    return (
        f"tasks={overview['task_count']} "
        f"variants={overview['variant_count']} "
        f"agents={overview['agent_count']} "
        f"trials={overview['trial_count']} "
        f"cases={overview['case_count']} "
        f"failed={overview['failed_count']} "
        f"timeouts={overview['timeout_count']} "
        f"low_confidence={overview['low_confidence_count']} "
        f"telemetry_gaps={overview['telemetry_gap_count']} "
        f"hard_failed={overview.get('hard_evaluation_failed_count', 0)} "
        f"soft_payloads={overview.get('soft_evaluation_payload_count', 0)}"
    )


def matrix_cell_rows(results: list[CaseResult]) -> list[dict[str, object]]:
    by_cell: dict[tuple[str, str], list[CaseResult]] = defaultdict(list)
    for result in results:
        by_cell[(result.task_id, result.variant)].append(result)

    rows: list[dict[str, object]] = []
    for (task_id, variant), items in sorted(by_cell.items()):
        statuses = format_counts(Counter(item.status for item in items), RUN_STATUS_ORDER)
        validations = format_counts(
            Counter(item.validation_status for item in items),
            VALIDATION_STATUS_ORDER,
        )
        confidences = format_counts(Counter(item.confidence for item in items), CONFIDENCE_ORDER)
        agents = ",".join(sorted({item.agent_name for item in items})) or "-"
        trials = ",".join(str(trial) for trial in sorted({item.trial_index for item in items}))
        pass_rate = _rate(
            items,
            lambda item: item.status == "completed" and item.validation_status == "passed",
        )
        summary = (
            f"cases={len(items)}; "
            f"pass_rate={pass_rate:.1%}; "
            f"statuses={statuses}; "
            f"validation={validations}; "
            f"confidence={confidences}; "
            f"agents={agents}; "
            f"trials={trials}"
        )
        rows.append(
            {
                "task_id": task_id,
                "variant": variant,
                "cases": len(items),
                "pass_rate": pass_rate,
                "status_counts": statuses,
                "validation_counts": validations,
                "confidence_counts": confidences,
                "agents": agents,
                "trials": trials,
                "summary": summary,
            }
        )
    return rows


def matrix_cell_grid(results: list[CaseResult]) -> dict[str, dict[str, dict[str, object]]]:
    grid: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in matrix_cell_rows(results):
        grid[str(row["task_id"])][str(row["variant"])] = row
    return dict(sorted(grid.items()))


def is_failed_result(result: CaseResult) -> bool:
    return result.status != "completed" or result.validation_status == "failed"


def is_timeout_result(result: CaseResult) -> bool:
    return result.status == "timeout" or result.timeout


def has_telemetry_gap(result: CaseResult) -> bool:
    return result.telemetry_status != "collected" or bool(result.telemetry_evidence_gaps)


def format_optional_int(value: int | None) -> str:
    return "-" if value is None else str(value)


def format_optional_number(value: float | int | None) -> str:
    return "-" if value is None else f"{float(value):.2f}"


def format_status_counts(value: dict[str, int]) -> str:
    return ",".join(f"{status}={count}" for status, count in value.items()) or "-"


def status_counts_map(counts: Counter[str]) -> dict[str, int]:
    return ordered_counts_map(counts, TELEMETRY_STATUS_ORDER)


def ordered_counts_map(counts: Counter[str], order: list[str]) -> dict[str, int]:
    ordered: dict[str, int] = {}
    for status in order:
        if counts[status]:
            ordered[status] = counts[status]
    for status in sorted(counts):
        if status not in ordered and counts[status]:
            ordered[status] = counts[status]
    return ordered


def format_counts(counts: Counter[str], order: list[str]) -> str:
    return format_status_counts(ordered_counts_map(counts, order))


def _rate(items: list[CaseResult], predicate) -> float:
    return sum(1 for item in items if predicate(item)) / len(items) if items else 0.0


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
