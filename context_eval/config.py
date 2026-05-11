from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from context_eval.logging import run_command
from context_eval.models import ContextEvalConfig, TaskFile


class ConfigError(RuntimeError):
    """Raised when a config or task file cannot be loaded."""


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"YAML file does not exist: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"YAML root must be a mapping: {path}")
    return data


def _resolve_path(value: Path, base_dir: Path) -> Path:
    return value if value.is_absolute() else (base_dir / value).resolve()


def load_config(path: Path) -> ContextEvalConfig:
    config_path = path.resolve()
    data = _read_yaml(config_path)
    try:
        config = ContextEvalConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_errors(config_path, exc, data)) from exc

    base_dir = config_path.parent
    config.config_path = config_path
    config.repo.path = _resolve_path(config.repo.path, base_dir)
    config.tasks = _resolve_path(config.tasks, base_dir)
    if config.agent.prompt_template:
        config.agent.prompt_template = _resolve_path(config.agent.prompt_template, base_dir)

    if "output_dir" in data:
        config.output_dir = _resolve_path(config.output_dir, base_dir)
    else:
        config.output_dir = (Path.cwd() / config.output_dir).resolve()

    for variant in config.variants.values():
        for overlay in variant.overlays:
            overlay.source = _resolve_path(overlay.source, base_dir)

    return config


def load_tasks(path: Path) -> TaskFile:
    task_path = path.resolve()
    data = _read_yaml(task_path)
    duplicate_task_id = _find_duplicate_task_id(data)
    if duplicate_task_id is not None:
        raise ConfigError(f"{task_path}: tasks[{duplicate_task_id}].id: duplicate task id")
    try:
        return TaskFile.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_errors(task_path, exc, data)) from exc


def filter_tasks(
    task_file: TaskFile,
    *,
    task_ids: list[str] | None = None,
    categories: list[str] | None = None,
    difficulties: list[str] | None = None,
) -> TaskFile:
    selected_task_ids = task_ids or []
    selected_categories = categories or []
    selected_difficulties = difficulties or []

    known_ids = {task.id for task in task_file.tasks}
    unknown_ids = [task_id for task_id in selected_task_ids if task_id not in known_ids]
    if unknown_ids:
        raise ConfigError(f"unknown task id(s): {', '.join(unknown_ids)}")

    tasks = list(task_file.tasks)
    if selected_task_ids:
        allowed = set(selected_task_ids)
        tasks = [task for task in tasks if task.id in allowed]
    if selected_categories:
        allowed = set(selected_categories)
        tasks = [task for task in tasks if task.category in allowed]
    if selected_difficulties:
        allowed = set(selected_difficulties)
        tasks = [task for task in tasks if task.difficulty in allowed]

    if (selected_task_ids or selected_categories or selected_difficulties) and not tasks:
        raise ConfigError("task filters selected no tasks")

    return TaskFile(tasks=tasks)


def validate_config_files(
    config_path: Path,
    tasks_override: Path | None = None,
    *,
    strict: bool = False,
) -> tuple[ContextEvalConfig, TaskFile]:
    config = load_config(config_path)
    tasks_path = tasks_override.resolve() if tasks_override else config.tasks
    tasks = load_tasks(tasks_path)

    if not config.repo.path.exists():
        raise ConfigError(f"{config.config_path}: repo.path does not exist: {config.repo.path}")
    if config.agent.prompt_template and not config.agent.prompt_template.exists():
        raise ConfigError(
            f"{config.config_path}: agent.prompt_template does not exist: "
            f"{config.agent.prompt_template}"
        )
    for name, variant in config.variants.items():
        for index, overlay in enumerate(variant.overlays):
            if not overlay.source.exists():
                raise ConfigError(
                    f"{config.config_path}: variants.{name}.overlays[{index}].source "
                    f"does not exist: {overlay.source}"
                )

    if strict:
        _validate_strict_config(config, tasks)

    return config, tasks


def _validate_strict_config(config: ContextEvalConfig, tasks: TaskFile) -> None:
    repo_check = run_command(
        ["git", "-C", str(config.repo.path), "rev-parse", "--is-inside-work-tree"],
        cwd=config.repo.path,
        shell=False,
    )
    if repo_check.exit_code != 0 or repo_check.stdout.strip() != "true":
        raise ConfigError(f"repo.path is not a Git repository: {config.repo.path}")

    _require_git_ref(
        config.repo.path,
        config.repo.base_ref,
        f"repo.base_ref does not resolve: {config.repo.base_ref}",
    )
    for task in tasks.tasks:
        if task.repo_ref:
            _require_git_ref(
                config.repo.path,
                task.repo_ref,
                f"task '{task.id}' repo_ref does not resolve: {task.repo_ref}",
            )


def _require_git_ref(repo_path: Path, ref: str, message: str) -> None:
    result = run_command(
        ["git", "-C", str(repo_path), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=repo_path,
        shell=False,
    )
    if result.exit_code != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f" ({detail})" if detail else ""
        raise ConfigError(f"{message}{suffix}")


def _format_validation_errors(path: Path, exc: ValidationError, data: dict[str, Any]) -> str:
    messages: list[str] = []
    for error in exc.errors(include_url=False, include_input=False):
        field_path = _format_error_location(error.get("loc", ()), data)
        message = str(error.get("msg", "invalid value"))
        messages.append(f"{path}: {field_path}: {message}")
    return "\n".join(messages)


def _format_error_location(loc: tuple[Any, ...], data: dict[str, Any]) -> str:
    if not loc:
        return "root"

    parts: list[str] = []
    previous: str | None = None
    for item in loc:
        if isinstance(item, int):
            label = _task_id_for_index(data, item) if previous == "tasks" else str(item)
            if parts:
                parts[-1] = f"{parts[-1]}[{label}]"
            else:
                parts.append(f"[{label}]")
            continue
        segment = str(item)
        parts.append(segment)
        previous = segment
    return ".".join(parts)


def _task_id_for_index(data: dict[str, Any], index: int) -> str:
    tasks = data.get("tasks")
    if isinstance(tasks, list) and 0 <= index < len(tasks):
        task = tasks[index]
        if isinstance(task, dict):
            task_id = task.get("id")
            if isinstance(task_id, str) and task_id.strip():
                return task_id.strip()
    return str(index)


def _find_duplicate_task_id(data: dict[str, Any]) -> str | None:
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return None

    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str):
            continue
        normalized = task_id.strip()
        if not normalized:
            continue
        if normalized in seen:
            return normalized
        seen.add(normalized)
    return None
