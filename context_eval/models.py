from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from context_eval import __version__

RESULT_SCHEMA_VERSION = "1"
RunStatus = Literal[
    "completed",
    "agent_failed",
    "timeout",
    "overlay_failed",
    "workspace_failed",
    "validation_failed",
    "internal_error",
]
ValidationStatus = Literal["passed", "failed", "skipped"]
Confidence = Literal["high", "medium", "low"]
CleanupStatus = Literal["skipped", "succeeded", "failed"]


class RepoConfig(BaseModel):
    path: Path
    base_ref: str = "HEAD"


class AgentConfig(BaseModel):
    name: str
    command: str
    timeout_minutes: int = Field(default=60, ge=1)
    network: str = "disabled"


class OverlayConfig(BaseModel):
    source: Path
    target: str

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        normalized = value.replace("\\", "/").strip()
        if not normalized:
            raise ValueError("overlay target must not be empty")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("overlay target must be a safe relative path")
        return path.as_posix()


class VariantConfig(BaseModel):
    description: str = ""
    overlays: list[OverlayConfig] = Field(default_factory=list)


class EvaluationConfig(BaseModel):
    commands: list[str] = Field(default_factory=list)


class ContextEvalConfig(BaseModel):
    repo: RepoConfig
    agent: AgentConfig
    variants: dict[str, VariantConfig]
    tasks: Path = Path("tasks.yaml")
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    output_dir: Path = Path(".context-eval/runs")
    config_path: Path | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def validate_variants(self) -> ContextEvalConfig:
        if not self.variants:
            raise ValueError("at least one context variant is required")
        return self


class ValidationConfig(BaseModel):
    commands: list[str] = Field(default_factory=list)


class TaskConfig(BaseModel):
    id: str
    prompt: str
    repo_ref: str | None = None
    title: str | None = None
    category: str | None = None
    difficulty: str | None = None
    validation: ValidationConfig = Field(default_factory=ValidationConfig)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("task id must not be empty")
        return stripped

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task prompt must not be empty")
        return value


class TaskFile(BaseModel):
    tasks: list[TaskConfig]

    @model_validator(mode="after")
    def validate_tasks(self) -> TaskFile:
        if not self.tasks:
            raise ValueError("at least one task is required")
        ids = [task.id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("task ids must be unique")
        return self


class CommandResult(BaseModel):
    command: str
    cwd: str
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float
    timeout: bool = False


class DiffStats(BaseModel):
    changed_files: int = 0
    insertions: int = 0
    deletions: int = 0
    touched_paths: list[str] = Field(default_factory=list)


class CaseResult(BaseModel):
    schema_version: str = RESULT_SCHEMA_VERSION
    context_eval_version: str = __version__
    run_id: str
    config_hash: str | None = None
    task_hash: str | None = None
    variant_hash: str | None = None
    case_id: str | None = None
    trial_index: int = 1
    task_id: str
    variant: str
    repo_ref: str
    agent_name: str
    network: str
    status: RunStatus
    timeout: bool = False
    agent_exit_code: int | None = None
    duration_seconds: float = 0.0
    workspace_path: str | None = None
    prompt_path: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    patch_path: str | None = None
    workspace_retained: bool = False
    cleanup_status: CleanupStatus = "skipped"
    changed_files: int = 0
    insertions: int = 0
    deletions: int = 0
    touched_paths: list[str] = Field(default_factory=list)
    validation_status: ValidationStatus = "skipped"
    confidence: Confidence = "low"
    validation_results: list[CommandResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
