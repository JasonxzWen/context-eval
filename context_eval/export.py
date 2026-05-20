from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from statistics import mean
from typing import Any

from context_eval.models import CaseResult
from context_eval.reporting import status_counts_map

EXPORT_SCHEMA_VERSION = "2"

CASE_COLUMNS = [
    "run_id",
    "case_id",
    "agent_name",
    "task_id",
    "variant",
    "trial_index",
    "status",
    "validation_status",
    "confidence",
    "telemetry_status",
    "telemetry_source",
    "telemetry_error",
    "duration_seconds",
    "agent_duration_seconds",
    "prompt_tokens",
    "cached_input_tokens",
    "completion_tokens",
    "total_tokens",
    "reasoning_tokens",
    "tool_call_count",
    "command_call_count",
    "tool_calls_by_name",
    "reasoning_step_count",
    "model_name",
    "provider_name",
    "telemetry_evidence_gaps",
    "codex_events_path",
    "codex_final_message_path",
    "codex_error_reason",
    "hard_evaluation_status",
    "hard_evaluation_score",
    "hard_evaluation_max_score",
    "hard_evaluation_passed_checks",
    "hard_evaluation_failed_checks",
    "soft_evaluation_status",
    "changed_files",
    "insertions",
    "deletions",
    "touched_paths",
]


def export_run_csv(run_dir: Path) -> str:
    results = _sorted_results(_load_results(run_dir))
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CASE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for result in results:
        writer.writerow(_case_csv_row(result))
    return output.getvalue()


def export_run_json(run_dir: Path, *, exported_at: datetime | None = None) -> str:
    results = _sorted_results(_load_results(run_dir))
    metadata = _load_metadata(run_dir)
    manual_reviews = _load_manual_reviews(run_dir)
    payload = {
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": _format_exported_at(exported_at),
        "source_files": _source_files(run_dir),
        "case_count": len(results),
        "agent_count": len({result.agent_name for result in results}),
        "variant_count": len({result.variant for result in results}),
        "task_count": len({result.task_id for result in results}),
        "run": {
            "run_id": metadata.get("run_id") or (results[0].run_id if results else run_dir.name),
            "metadata": metadata,
        },
        "evaluation_explanation": _evaluation_explanation(),
        "cases": [_case_json_row(result, manual_reviews=manual_reviews) for result in results],
        "manual_reviews": {
            "schema_version": "1",
            "reviews": manual_reviews,
        },
        "agent_summaries": agent_summary_rows(results),
    }
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _format_exported_at(value: datetime | None) -> str:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    timestamp = timestamp.astimezone(UTC)
    return timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def _source_files(run_dir: Path) -> list[str]:
    source_files = ["results.jsonl"]
    if (run_dir / "run_metadata.json").exists():
        source_files.append("run_metadata.json")
    if (run_dir / "manual_reviews.json").exists():
        source_files.append("manual_reviews.json")
    return source_files


def _evaluation_explanation() -> dict[str, Any]:
    return {
        "local_only": (
            "仅比较本地 artifact 中的观察结果，不是公开 benchmark、绝对排名或 agent "
            "leaderboard。"
        ),
        "validation_confidence": {
            "high": "有 validation commands 且全部通过。",
            "medium": "有 validation commands 但失败或超时。",
            "low": "没有 validation commands，不能做高置信判断。",
        },
        "hard_evaluation": {
            "score_meaning": "hard score 是通过检查数 / 可评分检查数，不是综合质量分。",
            "skipped_meaning": "skipped 表示缺少可评分本地产物，不能把缺失证据当作通过。",
        },
        "soft_evaluation": {
            "mode": "payload-only",
            "meaning": (
                "soft evaluation 目前只生成复核 payload，不自动调用 OpenAI、Claude 或其他 "
                "LLM judge。"
            ),
        },
        "manual_review": {
            "meaning": "manual review 是人工保存的复核证据和结论，不是自动评分。",
        },
        "evidence_limits": [
            "无 validation commands 时不能给高置信判断。",
            "hard check skipped 表示缺少可评分证据。",
            "telemetry missing 时 token、耗时和工具调用保持未知，不猜测。",
        ],
    }


def agent_summary_rows(results: list[CaseResult]) -> list[dict[str, Any]]:
    by_agent: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        by_agent[result.agent_name].append(result)

    summaries = []
    for agent_name, items in sorted(by_agent.items()):
        tool_counts: Counter[str] = Counter()
        model_counts: Counter[str] = Counter()
        telemetry_statuses: Counter[str] = Counter()
        for item in items:
            tool_counts.update(item.tool_calls_by_name)
            if item.model_name:
                model_counts.update([item.model_name])
            telemetry_statuses.update([item.telemetry_status])

        summaries.append(
            {
                "agent_name": agent_name,
                "cases": len(items),
                "pass_rate": _rate(
                    items,
                    lambda item: item.status == "completed"
                    and item.validation_status == "passed",
                ),
                "avg_duration_seconds": _mean(item.duration_seconds for item in items),
                "avg_agent_duration_seconds": _mean_optional(
                    item.agent_duration_seconds for item in items
                ),
                "avg_total_tokens": _mean_optional(item.total_tokens for item in items),
                "avg_tool_call_count": _mean_optional(item.tool_call_count for item in items),
                "avg_command_call_count": _mean_optional(
                    item.command_call_count for item in items
                ),
                "telemetry_statuses": status_counts_map(telemetry_statuses),
                "common_tool_names": _common_tool_names(tool_counts),
                "common_model_names": _common_model_names(model_counts),
            }
        )
    return summaries


def has_multiple_agents(results: list[CaseResult]) -> bool:
    return len({result.agent_name for result in results}) > 1


def _common_tool_names(tool_counts: Counter[str]) -> list[str]:
    return [
        name
        for name, _ in sorted(tool_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]


def _common_model_names(model_counts: Counter[str]) -> list[str]:
    return [
        name
        for name, _ in sorted(model_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]


def _sorted_results(results: list[CaseResult]) -> list[CaseResult]:
    return sorted(
        results,
        key=lambda result: (
            result.agent_name,
            result.task_id,
            result.variant,
            result.trial_index,
            result.case_id or "",
        ),
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


def _case_csv_row(result: CaseResult) -> dict[str, str | int]:
    return {
        "run_id": result.run_id,
        "case_id": result.case_id or "",
        "agent_name": result.agent_name,
        "task_id": result.task_id,
        "variant": result.variant,
        "trial_index": result.trial_index,
        "status": result.status,
        "validation_status": result.validation_status,
        "confidence": result.confidence,
        "hard_evaluation_status": result.hard_evaluation_status,
        "hard_evaluation_score": _format_optional_int(result.hard_evaluation_score),
        "hard_evaluation_max_score": _format_optional_int(result.hard_evaluation_max_score),
        "hard_evaluation_passed_checks": _format_optional_int(
            result.hard_evaluation_passed_checks
        ),
        "hard_evaluation_failed_checks": _format_optional_int(
            result.hard_evaluation_failed_checks
        ),
        "soft_evaluation_status": result.soft_evaluation_status,
        "changed_files": result.changed_files,
        "insertions": result.insertions,
        "deletions": result.deletions,
        "touched_paths": _format_list_csv(result.touched_paths),
        "telemetry_status": result.telemetry_status,
        "telemetry_source": result.telemetry_source,
        "telemetry_error": result.telemetry_error or "",
        "duration_seconds": _format_number(result.duration_seconds),
        "agent_duration_seconds": _format_optional_number(result.agent_duration_seconds),
        "prompt_tokens": _format_optional_int(result.prompt_tokens),
        "cached_input_tokens": _format_optional_int(result.cached_input_tokens),
        "completion_tokens": _format_optional_int(result.completion_tokens),
        "total_tokens": _format_optional_int(result.total_tokens),
        "reasoning_tokens": _format_optional_int(result.reasoning_tokens),
        "reasoning_step_count": _format_optional_int(result.reasoning_step_count),
        "tool_call_count": _format_optional_int(result.tool_call_count),
        "command_call_count": _format_optional_int(result.command_call_count),
        "tool_calls_by_name": _format_tool_calls_csv(result.tool_calls_by_name),
        "model_name": result.model_name or "",
        "provider_name": result.provider_name or "",
        "telemetry_evidence_gaps": _format_list_csv(result.telemetry_evidence_gaps),
        "codex_events_path": result.codex_events_path or "",
        "codex_final_message_path": result.codex_final_message_path or "",
        "codex_error_reason": result.codex_error_reason or "",
    }


def _case_json_row(
    result: CaseResult,
    *,
    manual_reviews: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    case_id = result.case_id or ""
    return {
        "run_id": result.run_id,
        "case_id": result.case_id,
        "agent_name": result.agent_name,
        "task_id": result.task_id,
        "variant": result.variant,
        "trial_index": result.trial_index,
        "status": result.status,
        "validation_status": result.validation_status,
        "confidence": result.confidence,
        "hard_evaluation_status": result.hard_evaluation_status,
        "hard_evaluation_score": result.hard_evaluation_score,
        "hard_evaluation_max_score": result.hard_evaluation_max_score,
        "hard_evaluation_passed_checks": result.hard_evaluation_passed_checks,
        "hard_evaluation_failed_checks": result.hard_evaluation_failed_checks,
        "hard_evaluation_path": result.hard_evaluation_path,
        "soft_evaluation_status": result.soft_evaluation_status,
        "soft_evaluation_payload_path": result.soft_evaluation_payload_path,
        "soft_evaluation_result_path": result.soft_evaluation_result_path,
        "changed_files": result.changed_files,
        "insertions": result.insertions,
        "deletions": result.deletions,
        "touched_paths": list(result.touched_paths),
        "telemetry_status": result.telemetry_status,
        "telemetry_source": result.telemetry_source,
        "telemetry_error": result.telemetry_error,
        "duration_seconds": result.duration_seconds,
        "agent_duration_seconds": result.agent_duration_seconds,
        "prompt_tokens": result.prompt_tokens,
        "cached_input_tokens": result.cached_input_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "reasoning_tokens": result.reasoning_tokens,
        "reasoning_step_count": result.reasoning_step_count,
        "tool_call_count": result.tool_call_count,
        "command_call_count": result.command_call_count,
        "tool_calls_by_name": dict(sorted(result.tool_calls_by_name.items())),
        "model_name": result.model_name,
        "provider_name": result.provider_name,
        "telemetry_evidence_gaps": list(result.telemetry_evidence_gaps),
        "codex_events_path": result.codex_events_path,
        "codex_final_message_path": result.codex_final_message_path,
        "codex_error_reason": result.codex_error_reason,
        "manual_review": (manual_reviews or {}).get(
            case_id,
            {
                "case_id": case_id,
                "decision": "not_reviewed",
                "confidence": "unknown",
                "reviewer": "",
                "notes": "",
                "updated_at": None,
            },
        ),
    }


def _load_manual_reviews(run_dir: Path) -> dict[str, dict[str, Any]]:
    path = run_dir / "manual_reviews.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    reviews = data.get("reviews", {}) if isinstance(data, dict) else {}
    if not isinstance(reviews, dict):
        return {}
    return {
        str(case_id): review
        for case_id, review in reviews.items()
        if isinstance(review, dict)
    }


def _rate(items: list[CaseResult], predicate) -> float:
    return sum(1 for item in items if predicate(item)) / len(items) if items else 0.0


def _mean(values) -> float | None:
    items = list(values)
    return mean(items) if items else None


def _mean_optional(values) -> float | None:
    items = [value for value in values if value is not None]
    return mean(items) if items else None


def _format_number(value: float | int) -> str:
    return f"{float(value):.2f}"


def _format_optional_number(value: float | int | None) -> str:
    return "" if value is None else _format_number(value)


def _format_optional_int(value: int | None) -> str:
    return "" if value is None else str(value)


def _format_tool_calls_csv(value: dict[str, int]) -> str:
    if not value:
        return ""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _format_list_csv(value: list[str]) -> str:
    if not value:
        return ""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
