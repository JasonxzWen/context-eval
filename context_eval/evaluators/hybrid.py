from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from context_eval.models import (
    CaseResult,
    HardEvaluationConfig,
    SnippetCheckConfig,
    TaskConfig,
)

HARD_EVALUATION_SCHEMA_VERSION = "1"
SOFT_EVALUATION_PAYLOAD_SCHEMA_VERSION = "1"
PATCH_EXCERPT_LIMIT = 12000


class HardEvaluationCheck(BaseModel):
    name: str
    status: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class HardEvaluationArtifact(BaseModel):
    schema_version: str = HARD_EVALUATION_SCHEMA_VERSION
    case_id: str
    task_id: str
    variant: str
    agent_name: str
    passed: bool
    score: int
    max_score: int
    checks: list[HardEvaluationCheck]
    summary: str


def run_hard_evaluation(
    *,
    result: CaseResult,
    task: TaskConfig,
    run_dir: Path,
    workspace: Path | None,
) -> HardEvaluationArtifact | None:
    config = task.hard_evaluation
    if config is None or not config.enabled:
        return None

    patch_text = _read_optional_run_path(run_dir, result.patch_path)
    touched_paths = set(result.touched_paths)
    checks: list[HardEvaluationCheck] = []

    checks.append(_agent_completion_check(result))
    if config.require_validation_pass:
        checks.append(_validation_check(result))

    for path in _required_paths(task, config):
        checks.append(
            _check(
                name=f"required_path:{path}",
                passed=path in touched_paths,
                passed_message=f"{path} changed",
                failed_message=f"{path} did not change",
                evidence={"path": path, "touched_paths": sorted(touched_paths)},
            )
        )

    forbidden_paths = _unique([*config.forbidden_paths, *_expected_forbidden_paths(task)])
    if forbidden_paths:
        touched_forbidden = sorted(path for path in forbidden_paths if path in touched_paths)
        checks.append(
            _check(
                name="forbidden_paths",
                passed=not touched_forbidden,
                passed_message="no forbidden paths changed",
                failed_message="forbidden paths changed",
                evidence={
                    "forbidden_paths": forbidden_paths,
                    "touched_forbidden_paths": touched_forbidden,
                },
            )
        )

    if config.max_changed_files is not None:
        checks.append(
            _check(
                name="max_changed_files",
                passed=result.changed_files <= config.max_changed_files,
                passed_message="changed file count is within limit",
                failed_message="changed file count exceeds limit",
                evidence={
                    "changed_files": result.changed_files,
                    "max_changed_files": config.max_changed_files,
                },
            )
        )

    checks.extend(_diff_bound_checks(result, config))
    checks.extend(
        _snippet_checks(
            checks=_expected_snippet_checks(task, config),
            workspace=workspace,
            patch_text=patch_text,
            expected=True,
        )
    )
    checks.extend(
        _snippet_checks(
            checks=_forbidden_snippet_checks(task, config),
            workspace=workspace,
            patch_text=patch_text,
            expected=False,
        )
    )

    scored = [check for check in checks if check.status != "skipped"]
    passed = sum(1 for check in scored if check.status == "passed")
    failed = sum(1 for check in scored if check.status == "failed")
    artifact = HardEvaluationArtifact(
        case_id=result.case_id or f"{result.task_id}__{result.variant}",
        task_id=result.task_id,
        variant=result.variant,
        agent_name=result.agent_name,
        passed=failed == 0,
        score=passed,
        max_score=len(scored),
        checks=checks,
        summary="passed" if failed == 0 else f"{failed} failed check(s)",
    )

    artifact_path = run_dir / "artifacts" / artifact.case_id / "hard_evaluation.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        artifact.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    result.hard_evaluation_status = "passed" if artifact.passed else "failed"
    result.hard_evaluation_score = artifact.score
    result.hard_evaluation_max_score = artifact.max_score
    result.hard_evaluation_passed_checks = passed
    result.hard_evaluation_failed_checks = failed
    result.hard_evaluation_path = artifact_path.relative_to(run_dir).as_posix()
    return artifact


def write_soft_evaluation_payload(
    *,
    result: CaseResult,
    task: TaskConfig,
    run_dir: Path,
    hard_evaluation: HardEvaluationArtifact | None,
) -> Path | None:
    config = task.soft_evaluation
    if config is None or not config.enabled:
        return None

    patch_text = _read_optional_run_path(run_dir, result.patch_path)
    payload = {
        "schema_version": SOFT_EVALUATION_PAYLOAD_SCHEMA_VERSION,
        "case": {
            "case_id": result.case_id,
            "run_id": result.run_id,
            "task_id": result.task_id,
            "variant": result.variant,
            "agent_name": result.agent_name,
            "status": result.status,
        },
        "task": {
            "title": task.title,
            "prompt": task.prompt,
            "category": task.category,
            "difficulty": task.difficulty,
            "repo_ref": result.repo_ref,
        },
        "expected_outcome": (
            task.expected_outcome.model_dump(mode="json")
            if task.expected_outcome is not None
            else None
        ),
        "rubric": [item.model_dump(mode="json") for item in config.rubric],
        "max_score": config.max_score,
        "changed_files": result.changed_files,
        "insertions": result.insertions,
        "deletions": result.deletions,
        "touched_paths": result.touched_paths,
        "patch_excerpt": patch_text[:PATCH_EXCERPT_LIMIT],
        "validation": {
            "status": result.validation_status,
            "confidence": result.confidence,
            "results": [item.model_dump(mode="json") for item in result.validation_results],
        },
        "hard_evaluation": (
            {
                "status": result.hard_evaluation_status,
                "score": result.hard_evaluation_score,
                "max_score": result.hard_evaluation_max_score,
                "summary": hard_evaluation.summary,
                "path": result.hard_evaluation_path,
            }
            if hard_evaluation is not None
            else {
                "status": result.hard_evaluation_status,
                "score": result.hard_evaluation_score,
                "max_score": result.hard_evaluation_max_score,
                "path": result.hard_evaluation_path,
            }
        ),
        "artifacts": {
            "prompt_path": result.prompt_path,
            "patch_path": result.patch_path,
            "stdout_path": result.stdout_path,
            "stderr_path": result.stderr_path,
            "hard_evaluation_path": result.hard_evaluation_path,
        },
        "logs": [
            path
            for path in [result.stdout_path, result.stderr_path]
            if path is not None
        ],
    }
    case_id = result.case_id or f"{result.task_id}__{result.variant}"
    payload_path = run_dir / "artifacts" / case_id / "soft_evaluation_payload.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result.soft_evaluation_status = "payload_generated"
    result.soft_evaluation_payload_path = payload_path.relative_to(run_dir).as_posix()
    return payload_path


def _agent_completion_check(result: CaseResult) -> HardEvaluationCheck:
    failed = result.timeout or result.status in {
        "agent_failed",
        "timeout",
        "workspace_failed",
        "overlay_failed",
        "internal_error",
    }
    return _check(
        name="agent_completed",
        passed=not failed,
        passed_message="agent completed without execution failure",
        failed_message="agent did not complete cleanly",
        evidence={
            "status": result.status,
            "timeout": result.timeout,
            "agent_exit_code": result.agent_exit_code,
        },
    )


def _validation_check(result: CaseResult) -> HardEvaluationCheck:
    return _check(
        name="validation_passed",
        passed=result.validation_status == "passed",
        passed_message="validation passed",
        failed_message="validation did not pass",
        evidence={"validation_status": result.validation_status},
    )


def _diff_bound_checks(
    result: CaseResult,
    config: HardEvaluationConfig,
) -> list[HardEvaluationCheck]:
    checks: list[HardEvaluationCheck] = []
    bounds = [
        ("min_insertions", result.insertions, config.min_insertions, ">="),
        ("max_insertions", result.insertions, config.max_insertions, "<="),
        ("min_deletions", result.deletions, config.min_deletions, ">="),
        ("max_deletions", result.deletions, config.max_deletions, "<="),
    ]
    for name, actual, expected, operator in bounds:
        if expected is None:
            continue
        passed = actual >= expected if operator == ">=" else actual <= expected
        checks.append(
            _check(
                name=name,
                passed=passed,
                passed_message=f"{name} satisfied",
                failed_message=f"{name} not satisfied",
                evidence={"actual": actual, "expected": expected, "operator": operator},
            )
        )
    return checks


def _snippet_checks(
    *,
    checks: list[SnippetCheckConfig],
    workspace: Path | None,
    patch_text: str,
    expected: bool,
) -> list[HardEvaluationCheck]:
    rows: list[HardEvaluationCheck] = []
    for check in checks:
        source_text, source = _snippet_source(check.path, workspace, patch_text)
        for snippet in check.snippets:
            name = (
                f"expected_snippet:{check.path}"
                if expected
                else f"forbidden_snippet:{check.path}"
            )
            if source_text is None:
                rows.append(
                    HardEvaluationCheck(
                        name=name,
                        status="skipped",
                        message="no retained file or patch text available for snippet check",
                        evidence={"path": check.path, "snippet": snippet},
                    )
                )
                continue
            contains = snippet in source_text
            passed = contains if expected else not contains
            rows.append(
                _check(
                    name=name,
                    passed=passed,
                    passed_message=(
                        "expected snippet found"
                        if expected
                        else "forbidden snippet absent"
                    ),
                    failed_message=(
                        "expected snippet missing"
                        if expected
                        else "forbidden snippet found"
                    ),
                    evidence={"path": check.path, "snippet": snippet, "source": source},
                )
            )
    return rows


def _snippet_source(
    path: str,
    workspace: Path | None,
    patch_text: str,
) -> tuple[str | None, str | None]:
    if workspace is not None:
        candidate = workspace / path
        if candidate.exists() and candidate.is_file():
            return candidate.read_text(encoding="utf-8", errors="replace"), "workspace"
    if patch_text:
        return patch_text, "patch"
    return None, None


def _required_paths(task: TaskConfig, config: HardEvaluationConfig) -> list[str]:
    paths = list(config.required_paths)
    if task.expected_outcome is not None:
        paths.extend(item.path for item in task.expected_outcome.files if item.must_change)
    return _unique(paths)


def _expected_forbidden_paths(task: TaskConfig) -> list[str]:
    if task.expected_outcome is None:
        return []
    return list(task.expected_outcome.forbidden_paths)


def _expected_snippet_checks(
    task: TaskConfig,
    config: HardEvaluationConfig,
) -> list[SnippetCheckConfig]:
    checks = list(config.expected_snippets)
    if task.expected_outcome is not None:
        for file in task.expected_outcome.files:
            if file.expected_snippets:
                checks.append(
                    SnippetCheckConfig(path=file.path, snippets=file.expected_snippets)
                )
    return _unique_snippet_checks(checks)


def _forbidden_snippet_checks(
    task: TaskConfig,
    config: HardEvaluationConfig,
) -> list[SnippetCheckConfig]:
    checks = list(config.forbidden_snippets)
    if task.expected_outcome is not None:
        for file in task.expected_outcome.files:
            if file.forbidden_snippets:
                checks.append(
                    SnippetCheckConfig(path=file.path, snippets=file.forbidden_snippets)
                )
    return _unique_snippet_checks(checks)


def _unique_snippet_checks(checks: list[SnippetCheckConfig]) -> list[SnippetCheckConfig]:
    seen: set[tuple[str, str]] = set()
    unique_checks: list[SnippetCheckConfig] = []
    for check in checks:
        snippets: list[str] = []
        for snippet in check.snippets:
            key = (check.path, snippet)
            if key in seen:
                continue
            seen.add(key)
            snippets.append(snippet)
        if snippets:
            unique_checks.append(SnippetCheckConfig(path=check.path, snippets=snippets))
    return unique_checks


def _check(
    *,
    name: str,
    passed: bool,
    passed_message: str,
    failed_message: str,
    evidence: dict[str, Any],
) -> HardEvaluationCheck:
    return HardEvaluationCheck(
        name=name,
        status="passed" if passed else "failed",
        message=passed_message if passed else failed_message,
        evidence=evidence,
    )


def _read_optional_run_path(run_dir: Path, relative_path: str | None) -> str:
    if relative_path is None:
        return ""
    path = run_dir / relative_path
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
