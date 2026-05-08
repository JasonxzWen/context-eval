from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from rich.console import Console

from context_eval.inspect_run import _load_metadata, _load_results
from context_eval.models import CaseResult


def compare_run(run_dir: Path, console: Console) -> None:
    run_dir = run_dir.resolve()
    results = _load_results(run_dir)
    metadata = _load_metadata(run_dir)
    run_id = metadata.get("run_id") or (results[0].run_id if results else run_dir.name)

    console.print(f"[bold]Run:[/bold] {run_id}")
    console.print(f"Results: {len(results)}")
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
            }
        )
    return stats


def _rate(items: list[CaseResult], predicate) -> float:
    return sum(1 for item in items if predicate(item)) / len(items) if items else 0.0
