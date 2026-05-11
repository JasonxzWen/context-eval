from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from context_eval.models import ContextEvalConfig, TaskFile


class EditableRepo(BaseModel):
    path: str
    base_ref: str


class EditableAgent(BaseModel):
    name: str
    command: str
    timeout_minutes: int
    network: str


class EditableOverlay(BaseModel):
    source: str
    target: str


class EditableVariant(BaseModel):
    name: str
    description: str = ""
    overlays: list[EditableOverlay] = Field(default_factory=list)


class EditableTask(BaseModel):
    id: str
    prompt: str
    repo_ref: str | None = None
    title: str | None = None
    category: str | None = None
    difficulty: str | None = None
    validation_timeout_seconds: int | None = None
    validation_commands: list[str] = Field(default_factory=list)


class EditableConfigModel(BaseModel):
    repo: EditableRepo
    agent: EditableAgent
    tasks_path: str
    variants: list[EditableVariant]
    tasks: list[EditableTask]
    evaluation_timeout_seconds: int | None = None
    evaluation_commands: list[str] = Field(default_factory=list)
    output_dir: str | None = None


class EditableYamlExport(BaseModel):
    config_yaml: str
    tasks_yaml: str


def build_editable_model(
    config: ContextEvalConfig,
    tasks: TaskFile,
) -> EditableConfigModel:
    """Convert loaded runtime config and tasks into a browser-editable model."""

    config_dir = config.config_path.parent if config.config_path else None
    source = _read_source_mapping(config.config_path)

    return EditableConfigModel(
        repo=EditableRepo(
            path=_source_path(source, ("repo", "path"), config.repo.path, config_dir),
            base_ref=config.repo.base_ref,
        ),
        agent=EditableAgent(
            name=config.agent.name,
            command=config.agent.command,
            timeout_minutes=config.agent.timeout_minutes,
            network=config.agent.network,
        ),
        tasks_path=_source_path(source, ("tasks",), config.tasks, config_dir),
        output_dir=_optional_source_path(source, "output_dir", config.output_dir, config_dir),
        variants=[
            EditableVariant(
                name=name,
                description=variant.description,
                overlays=[
                    EditableOverlay(
                        source=_overlay_source(source, name, index, overlay.source, config_dir),
                        target=overlay.target,
                    )
                    for index, overlay in enumerate(variant.overlays)
                ],
            )
            for name, variant in config.variants.items()
        ],
        tasks=[
            EditableTask(
                id=task.id,
                title=task.title,
                prompt=task.prompt,
                repo_ref=task.repo_ref,
                category=task.category,
                difficulty=task.difficulty,
                validation_timeout_seconds=task.validation.timeout_seconds,
                validation_commands=list(task.validation.commands),
            )
            for task in tasks.tasks
        ],
        evaluation_timeout_seconds=config.evaluation.timeout_seconds,
        evaluation_commands=list(config.evaluation.commands),
    )


def export_editable_yaml(model: EditableConfigModel) -> EditableYamlExport:
    """Serialize an editable model into separate config and task YAML documents."""

    issues = validate_editable_model(model)
    if issues:
        raise ValueError(f"export blocked: {'; '.join(issues)}")

    _require_unique("variant names", [variant.name for variant in model.variants])
    _require_unique("task ids", [task.id for task in model.tasks])

    config_data: dict[str, Any] = {
        "repo": {
            "path": model.repo.path,
            "base_ref": model.repo.base_ref,
        },
        "agent": {
            "name": model.agent.name,
            "command": model.agent.command,
            "timeout_minutes": model.agent.timeout_minutes,
            "network": model.agent.network,
        },
        "tasks": model.tasks_path,
        "variants": {
            variant.name: {
                "description": variant.description,
                "overlays": [
                    {
                        "source": overlay.source,
                        "target": overlay.target,
                    }
                    for overlay in variant.overlays
                ],
            }
            for variant in model.variants
        },
        "evaluation": _evaluation_to_yaml_data(model),
    }
    if model.output_dir is not None:
        config_data["output_dir"] = model.output_dir

    tasks_data = {
        "tasks": [_task_to_yaml_data(task) for task in model.tasks],
    }

    return EditableYamlExport(
        config_yaml=_dump_yaml(config_data),
        tasks_yaml=_dump_yaml(tasks_data),
    )


def validate_editable_model(model: EditableConfigModel) -> list[str]:
    """Return persistence blockers for an edited local UI model."""

    issues: list[str] = []
    _require_text(model.repo.path, "repo.path", issues)
    _require_text(model.repo.base_ref, "repo.base_ref", issues)
    _require_text(model.agent.name, "agent.name", issues)
    _require_text(model.agent.command, "agent.command", issues)
    _require_text(model.tasks_path, "tasks path", issues)

    if model.agent.timeout_minutes < 1:
        issues.append("agent.timeout_minutes must be a positive integer")
    if model.agent.network not in {"disabled", "enabled"}:
        issues.append("agent.network must be disabled or enabled")
    if (
        model.evaluation_timeout_seconds is not None
        and model.evaluation_timeout_seconds < 1
    ):
        issues.append("evaluation.timeout_seconds must be a positive integer")

    if not model.variants:
        issues.append("at least one variant is required")
    for variant_index, variant in enumerate(model.variants, start=1):
        _require_text(variant.name, f"variant {variant_index} name", issues)
        for overlay_index, overlay in enumerate(variant.overlays, start=1):
            label = f"variant {variant_index} overlay {overlay_index}"
            _require_text(overlay.source, f"{label} source", issues)
            _require_text(overlay.target, f"{label} target", issues)
            if not _is_safe_relative_path(overlay.target):
                issues.append(f"{label} target must be a safe relative path")

    if not model.tasks:
        issues.append("at least one task is required")
    for task_index, task in enumerate(model.tasks, start=1):
        _require_text(task.id, f"task {task_index} id", issues)
        _require_text(task.prompt, f"task {task_index} prompt", issues)
        if (
            task.validation_timeout_seconds is not None
            and task.validation_timeout_seconds < 1
        ):
            issues.append(
                f"task {task_index} validation.timeout_seconds must be a positive integer"
            )

    return issues


def _task_to_yaml_data(task: EditableTask) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": task.id,
    }
    if task.title is not None:
        data["title"] = task.title
    data["prompt"] = task.prompt
    if task.repo_ref is not None:
        data["repo_ref"] = task.repo_ref
    if task.category is not None:
        data["category"] = task.category
    if task.difficulty is not None:
        data["difficulty"] = task.difficulty
    if task.validation_commands or task.validation_timeout_seconds is not None:
        validation: dict[str, Any] = {}
        if task.validation_timeout_seconds is not None:
            validation["timeout_seconds"] = task.validation_timeout_seconds
        validation["commands"] = list(task.validation_commands)
        data["validation"] = validation
    return data


def _evaluation_to_yaml_data(model: EditableConfigModel) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if model.evaluation_timeout_seconds is not None:
        data["timeout_seconds"] = model.evaluation_timeout_seconds
    data["commands"] = list(model.evaluation_commands)
    return data


def _dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def _read_source_mapping(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _source_path(
    source: dict[str, Any],
    keys: tuple[str, ...],
    fallback: Path,
    base_dir: Path | None,
) -> str:
    value = _nested_value(source, keys)
    if isinstance(value, str):
        return value
    return _format_path(fallback, base_dir)


def _optional_source_path(
    source: dict[str, Any],
    key: str,
    fallback: Path,
    base_dir: Path | None,
) -> str | None:
    value = source.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return _format_path(fallback, base_dir)


def _overlay_source(
    source: dict[str, Any],
    variant_name: str,
    overlay_index: int,
    fallback: Path,
    base_dir: Path | None,
) -> str:
    raw_variant = source.get("variants", {}).get(variant_name, {})
    raw_overlays = raw_variant.get("overlays", []) if isinstance(raw_variant, dict) else []
    if overlay_index < len(raw_overlays):
        raw_overlay = raw_overlays[overlay_index]
        if isinstance(raw_overlay, dict) and isinstance(raw_overlay.get("source"), str):
            return raw_overlay["source"]
    return _format_path(fallback, base_dir)


def _nested_value(source: dict[str, Any], keys: tuple[str, ...]) -> Any:
    value: Any = source
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _format_path(path: Path, base_dir: Path | None) -> str:
    if base_dir is not None and path.is_absolute():
        try:
            relative = os.path.relpath(path, base_dir)
        except ValueError:
            return path.as_posix()
        normalized = Path(relative).as_posix()
        if normalized == "." or normalized.startswith("../"):
            return normalized
        return f"./{normalized}"
    return path.as_posix()


def _require_text(value: str | None, label: str, issues: list[str]) -> None:
    if value is None or value.strip() == "":
        issues.append(f"{label} is required")


def _is_safe_relative_path(value: str) -> bool:
    text = value.strip().replace("\\", "/")
    if text == "":
        return False
    if text.startswith("/"):
        return False
    if len(text) >= 2 and text[1] == ":" and text[0].isalpha():
        return False
    return ".." not in text.split("/")


def _require_unique(label: str, values: list[str]) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")
