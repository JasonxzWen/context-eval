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
        raise ConfigError(str(exc)) from exc

    base_dir = config_path.parent
    config.config_path = config_path
    config.repo.path = _resolve_path(config.repo.path, base_dir)
    config.tasks = _resolve_path(config.tasks, base_dir)

    if "output_dir" in data:
        config.output_dir = _resolve_path(config.output_dir, base_dir)
    else:
        config.output_dir = (Path.cwd() / config.output_dir).resolve()

    for variant in config.variants.values():
        for overlay in variant.overlays:
            overlay.source = _resolve_path(overlay.source, base_dir)

    return config


def load_tasks(path: Path) -> TaskFile:
    data = _read_yaml(path.resolve())
    try:
        return TaskFile.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


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
        raise ConfigError(f"repo.path does not exist: {config.repo.path}")
    for name, variant in config.variants.items():
        for overlay in variant.overlays:
            if not overlay.source.exists():
                raise ConfigError(
                    f"variant '{name}' overlay source does not exist: {overlay.source}"
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
