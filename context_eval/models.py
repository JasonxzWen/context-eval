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
CleanupPolicy = Literal["never", "always", "successful", "failed"]
TelemetryStatus = Literal["unavailable", "collected", "partial", "error"]
TelemetryCollectorKind = Literal["none", "json-file"]


class RepoConfig(BaseModel):
    path: Path
    base_ref: str = "HEAD"


class AgentTelemetryConfig(BaseModel):
    collector: TelemetryCollectorKind = "none"
    file: str = "telemetry.json"
    environment_variable: str | None = "CONTEXT_EVAL_TELEMETRY_FILE"

    @field_validator("file")
    @classmethod
    def validate_file(cls, value: str) -> str:
        normalized = value.replace("\\", "/").strip()
        if not normalized:
            raise ValueError("telemetry file must not be empty")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("telemetry file must be a safe relative path")
        return path.as_posix()

    @field_validator("environment_variable")
    @classmethod
    def validate_environment_variable(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("telemetry environment variable must not be empty")
        return stripped


class AgentConfig(BaseModel):
    name: str
    command: str
    prompt_template: Path | None = None
    timeout_minutes: int = Field(default=60, ge=1)
    network: str = "disabled"
    telemetry: AgentTelemetryConfig = Field(default_factory=AgentTelemetryConfig)


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
    timeout_seconds: int | None = Field(default=None, ge=1)


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
    timeout_seconds: int | None = Field(default=None, ge=1)


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
    telemetry_status: TelemetryStatus = "unavailable"
    telemetry_source: str = "none"
    telemetry_error: str | None = None
    agent_duration_seconds: float | None = Field(default=None, ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    tool_call_count: int | None = Field(default=None, ge=0)
    tool_calls_by_name: dict[str, int] = Field(default_factory=dict)
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

    @field_validator("tool_calls_by_name")
    @classmethod
    def validate_tool_calls_by_name(cls, value: dict[str, int]) -> dict[str, int]:
        for name, count in value.items():
            if not name.strip():
                raise ValueError("tool call names must not be empty")
            if count < 0:
                raise ValueError("tool call counts must be non-negative")
        return value
