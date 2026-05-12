from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from context_eval.export import agent_summary_rows, has_multiple_agents
from context_eval.models import CaseResult
from context_eval.reporting import (
    format_status_counts,
    has_telemetry_gap,
    is_failed_result,
    matrix_cell_grid,
    run_matrix_overview,
    telemetry_stats_by_variant,
)


def _load_results(run_dir: Path) -> list[CaseResult]:
    results_path = run_dir / "results.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(f"results file not found: {results_path}")
    results: list[CaseResult] = []
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            results.append(CaseResult.model_validate_json(line))
    return results


def _load_metadata(run_dir: Path) -> dict[str, Any]:
    metadata_path = run_dir / "run_metadata.json"
    if not metadata_path.exists():
        return {}
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _variant_stats(results: list[CaseResult]) -> list[dict[str, Any]]:
    by_variant: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        by_variant[result.variant].append(result)

    stats: list[dict[str, Any]] = []
    for variant, items in sorted(by_variant.items()):
        passed = sum(1 for item in items if item.validation_status == "passed")
        stats.append(
            {
                "variant": variant,
                "total": len(items),
                "passed": passed,
                "pass_rate": passed / len(items) if items else 0,
                "avg_duration": mean(item.duration_seconds for item in items) if items else 0,
                "avg_changed_files": mean(item.changed_files for item in items) if items else 0,
            }
        )
    return stats


def _matrix(results: list[CaseResult]) -> dict[str, dict[str, CaseResult]]:
    return matrix_cell_grid(results)


def _agent_stats(results: list[CaseResult]) -> list[dict[str, Any]]:
    if not has_multiple_agents(results):
        return []

    stats = []
    for item in agent_summary_rows(results):
        stats.append(
            {
                **item,
                "telemetry_statuses": format_status_counts(item["telemetry_statuses"]),
                "common_tool_names": ",".join(item["common_tool_names"]) or "-",
            }
        )
    return stats


def render_markdown_report(run_dir: Path) -> Path:
    run_dir = run_dir.resolve()
    results = _load_results(run_dir)
    metadata = _load_metadata(run_dir)
    failed_cases = [
        result
        for result in results
        if is_failed_result(result)
    ]
    low_confidence = [result for result in results if result.confidence == "low"]
    telemetry_gaps = [result for result in results if has_telemetry_gap(result)]

    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(default=False),
        trim_blocks=False,
        lstrip_blocks=False,
    )
    template = env.get_template("report.md.j2")
    body = template.render(
        run_dir=run_dir,
        metadata=metadata,
        results=results,
        overview=run_matrix_overview(results),
        matrix=_matrix(results),
        variants=sorted({result.variant for result in results}),
        variant_stats=_variant_stats(results),
        telemetry_stats=telemetry_stats_by_variant(results),
        agent_stats=_agent_stats(results),
        metadata_agent_names=_metadata_agent_names(metadata),
        failed_cases=failed_cases,
        low_confidence=low_confidence,
        telemetry_gaps=telemetry_gaps,
    )
    report_path = run_dir / "report.md"
    report_path.write_text(body, encoding="utf-8")
    return report_path


def _metadata_agent_names(metadata: dict[str, Any]) -> list[str]:
    agents = metadata.get("agents")
    if isinstance(agents, list):
        names = [
            item.get("name")
            for item in agents
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]
        if names:
            return names
    agent = metadata.get("agent")
    if isinstance(agent, dict) and isinstance(agent.get("name"), str):
        return [agent["name"]]
    return []
