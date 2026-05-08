from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from context_eval.models import CaseResult


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
    rows: dict[str, dict[str, CaseResult]] = defaultdict(dict)
    for result in results:
        rows[result.task_id][result.variant] = result
    return dict(sorted(rows.items()))


def render_markdown_report(run_dir: Path) -> Path:
    run_dir = run_dir.resolve()
    results = _load_results(run_dir)
    metadata = _load_metadata(run_dir)
    failed_cases = [
        result
        for result in results
        if result.status not in {"completed"} or result.validation_status == "failed"
    ]
    low_confidence = [result for result in results if result.confidence == "low"]

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
        matrix=_matrix(results),
        variants=sorted({result.variant for result in results}),
        variant_stats=_variant_stats(results),
        failed_cases=failed_cases,
        low_confidence=low_confidence,
    )
    report_path = run_dir / "report.md"
    report_path.write_text(body, encoding="utf-8")
    return report_path
