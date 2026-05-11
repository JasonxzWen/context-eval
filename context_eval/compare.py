from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from rich.console import Console

from context_eval.export import agent_summary_rows, has_multiple_agents
from context_eval.inspect_run import _load_metadata, _load_results
from context_eval.models import CaseResult
from context_eval.reporting import (
    format_matrix_overview_inline,
    format_optional_number,
    format_status_counts,
    matrix_cell_rows,
    run_matrix_overview,
    telemetry_summary,
)


def compare_run(run_dir: Path, console: Console) -> None:
    run_dir = run_dir.resolve()
    results = _load_results(run_dir)
    metadata = _load_metadata(run_dir)
    run_id = metadata.get("run_id") or (results[0].run_id if results else run_dir.name)

    console.print(f"[bold]Run:[/bold] {run_id}")
    console.print(f"Results: {len(results)}")
    console.print(
        "Local observations only; sourced from results.jsonl and optional run_metadata.json",
        soft_wrap=True,
    )
    console.print(
        f"Matrix: {format_matrix_overview_inline(run_matrix_overview(results))}",
        soft_wrap=True,
    )
    console.print("Variants:")
    for stat in _variant_stats(results):
        console.print(
            "- "
            f"variant={stat['variant']} "
            f"cases={stat['total']} "
            f"pass_rate={stat['pass_rate']:.1%} "
            f"timeout_rate={stat['timeout_rate']:.1%} "
            f"agent_failure_rate={stat['agent_failure_rate']:.1%} "
            f"validation_failure_rate={stat['validation_failure_rate']:.1%} "
            f"avg_duration={stat['avg_duration']:.2f} "
            f"avg_changed_files={stat['avg_changed_files']:.2f} "
            f"common_touched_paths={stat['common_touched_paths']}"
            f" telemetry_statuses={stat['telemetry_statuses']} "
            f"avg_agent_duration={format_optional_number(stat['avg_agent_duration_seconds'])} "
            f"avg_total_tokens={format_optional_number(stat['avg_total_tokens'])} "
            f"avg_tool_calls={format_optional_number(stat['avg_tool_calls'])} "
            f"common_tool_names={stat['common_tool_names']}"
        )

    if results:
        console.print("Matrix cells:")
        for cell in matrix_cell_rows(results):
            console.print(
                "cell "
                f"task={cell['task_id']} "
                f"variant={cell['variant']} "
                f"cases={cell['cases']} "
                f"pass_rate={float(cell['pass_rate']):.1%} "
                f"statuses={cell['status_counts']} "
                f"validation={cell['validation_counts']} "
                f"confidence={cell['confidence_counts']} "
                f"agents={cell['agents']} "
                f"trials={cell['trials']}",
                soft_wrap=True,
            )

    if has_multiple_agents(results):
        console.print("Agents:")
        for stat in agent_summary_rows(results):
            console.print(
                "- "
                f"agent={stat['agent_name']} "
                f"cases={stat['cases']} "
                f"pass_rate={float(stat['pass_rate']):.1%} "
                f"avg_duration={format_optional_number(stat['avg_duration_seconds'])} "
                f"avg_agent_duration={format_optional_number(stat['avg_agent_duration_seconds'])} "
                f"avg_total_tokens={format_optional_number(stat['avg_total_tokens'])} "
                f"avg_tool_calls={format_optional_number(stat['avg_tool_call_count'])} "
                f"telemetry_statuses={format_status_counts(stat['telemetry_statuses'])} "
                f"common_tool_names={','.join(stat['common_tool_names']) or '-'}"
            )


def _variant_stats(results: list[CaseResult]) -> list[dict[str, object]]:
    by_variant: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        by_variant[result.variant].append(result)

    stats: list[dict[str, object]] = []
    for variant, items in sorted(by_variant.items()):
        total = len(items)
        touched_paths = Counter(path for item in items for path in item.touched_paths)
        common_paths = ",".join(path for path, _ in touched_paths.most_common(5)) or "-"
        telemetry = telemetry_summary(items)
        stats.append(
            {
                "variant": variant,
                "total": total,
                "pass_rate": _rate(
                    items,
                    lambda item: item.status == "completed"
                    and item.validation_status == "passed",
                ),
                "timeout_rate": _rate(items, lambda item: item.status == "timeout" or item.timeout),
                "agent_failure_rate": _rate(items, lambda item: item.status == "agent_failed"),
                "validation_failure_rate": _rate(
                    items,
                    lambda item: item.status == "validation_failed"
                    or item.validation_status == "failed",
                ),
                "avg_duration": mean(item.duration_seconds for item in items) if items else 0.0,
                "avg_changed_files": mean(item.changed_files for item in items) if items else 0.0,
                "common_touched_paths": common_paths,
                **telemetry,
            }
        )
    return stats


def _rate(items: list[CaseResult], predicate) -> float:
    return sum(1 for item in items if predicate(item)) / len(items) if items else 0.0
