from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from context_eval.export import agent_summary_rows, has_multiple_agents
from context_eval.models import CaseResult
from context_eval.reporting import (
    format_optional_int,
    format_optional_number,
    format_status_counts,
)


def inspect_run(run_dir: Path, console: Console) -> None:
    run_dir = run_dir.resolve()
    results = _load_results(run_dir)
    metadata = _load_metadata(run_dir)
    run_id = metadata.get("run_id") or (results[0].run_id if results else run_dir.name)

    console.print(f"[bold]Run:[/bold] {run_id}")
    console.print(f"Results: {len(results)}")
    if metadata:
        agent = metadata.get("agent", {}).get("name")
        base_ref = metadata.get("repo", {}).get("base_ref")
        if agent:
            console.print(f"Agent: {agent}")
        if base_ref:
            console.print(f"Base ref: {base_ref}")

    console.print("Cases:")
    for result in results:
        case_id = result.case_id or f"{result.task_id}__{result.variant}"
        console.print(
            "- "
            f"case={case_id} "
            f"task={result.task_id} "
            f"variant={result.variant} "
            f"trial={result.trial_index} "
            f"status={result.status} "
            f"validation={result.validation_status} "
            f"confidence={result.confidence} "
            f"changed_files={result.changed_files}"
            f" telemetry_status={result.telemetry_status} "
            f"telemetry_source={result.telemetry_source} "
            f"agent_duration={format_optional_number(result.agent_duration_seconds)} "
            f"total_tokens={format_optional_int(result.total_tokens)} "
            f"tool_calls={format_optional_int(result.tool_call_count)}"
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


def _load_results(run_dir: Path) -> list[CaseResult]:
    results_path = run_dir / "results.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(f"results file not found: {results_path}")

    results: list[CaseResult] = []
    for line_number, line in enumerate(results_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            results.append(CaseResult.model_validate_json(line))
        except Exception as exc:
            raise ValueError(f"malformed results.jsonl line {line_number}: {exc}") from exc
    return results


def _load_metadata(run_dir: Path) -> dict[str, Any]:
    metadata_path = run_dir / "run_metadata.json"
    if not metadata_path.exists():
        return {}
    return json.loads(metadata_path.read_text(encoding="utf-8"))
