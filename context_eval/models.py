from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from string import Formatter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
AgentProfileKind = Literal["codex-cli", "claude-code", "traecli", "coco", "custom"]
HardEvaluationStatus = Literal["not_configured", "passed", "failed", "skipped"]
SoftEvaluationStatus = Literal[
    "not_configured",
    "payload_generated",
    "result_available",
    "skipped",
    "error",
]

SUPPORTED_AGENT_COMMAND_VARIABLES = frozenset(
    {
        "workspace",
        "prompt",
        "prompt_file",
        "task_id",
        "variant",
        "output_dir",
        "telemetry_file",
    }
)


def command_template_variables(template: str) -> set[str]:
    variables: set[str] = set()
    try:
        parsed = list(Formatter().parse(template))
    except ValueError as exc:
        raise ValueError(f"invalid agent command template: {exc}") from exc

    for _, field_name, format_spec, _ in parsed:
        if field_name is None:
            continue
        if not field_name:
            raise ValueError("agent command template references empty variable")
        variables.add(field_name)
        if format_spec:
            variables.update(command_template_variables(format_spec))
    return variables


def validate_agent_command_template(
    template: str,
    *,
    allowed_variables: set[str] | frozenset[str] | None = None,
) -> None:
    allowed = set(allowed_variables or SUPPORTED_AGENT_COMMAND_VARIABLES)
    unknown = sorted(command_template_variables(template) - allowed)
    if unknown:
        raise ValueError(
            f"agent command template references unknown variable: {unknown[0]}"
        )


def render_agent_command_preview(
    template: str,
    *,
    workspace: Path,
    prompt: str,
    prompt_file: Path,
    task_id: str,
    variant: str,
    output_dir: Path,
    telemetry_file: Path | None = None,
    extra_variables: dict[str, str] | None = None,
) -> str:
    variables = {
        "workspace": str(workspace),
        "prompt": prompt,
        "prompt_file": str(prompt_file),
        "task_id": task_id,
        "variant": variant,
        "output_dir": str(output_dir),
    }
    if telemetry_file is not None:
        variables["telemetry_file"] = str(telemetry_file)
    if extra_variables:
        variables.update(extra_variables)
    validate_agent_command_template(template, allowed_variables=set(variables))
    return template.format(**variables)


def validate_repo_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    if not normalized:
        raise ValueError("path must not be empty")
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or PureWindowsPath(normalized).is_absolute()
        or ".." in path.parts
    ):
        raise ValueError("path must be a safe repository-relative path")
    return path.as_posix()


def _validate_repo_relative_paths(values: list[str]) -> list[str]:
    return [validate_repo_relative_path(value) for value in values]


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
        if (
            path.is_absolute()
            or PureWindowsPath(normalized).is_absolute()
            or ".." in path.parts
        ):
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


class AgentProfileFields(BaseModel):
    command: str
    prompt_template: Path | None = None
    timeout_minutes: int = Field(default=60, ge=1)
    network: str = "disabled"
    telemetry: AgentTelemetryConfig = Field(default_factory=AgentTelemetryConfig)

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("agent command must not be empty")
        command_template_variables(value)
        return value


class AgentProfileConfig(AgentProfileFields):
    kind: AgentProfileKind

    def to_agent_config(self, name: str) -> AgentConfig:
        return AgentConfig(
            name=name,
            kind=self.kind,
            command=self.command,
            prompt_template=self.prompt_template,
            timeout_minutes=self.timeout_minutes,
            network=self.network,
            telemetry=self.telemetry,
        )


class AgentConfig(AgentProfileFields):
    name: str
    kind: AgentProfileKind = "custom"

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("agent name must not be empty")
        return stripped


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
        if (
            path.is_absolute()
            or PureWindowsPath(normalized).is_absolute()
            or ".." in path.parts
        ):
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
    agent: AgentConfig | None = None
    agents: dict[str, AgentProfileConfig] = Field(default_factory=dict)
    variants: dict[str, VariantConfig]
    tasks: Path = Path("tasks.yaml")
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    output_dir: Path = Path(".context-eval/runs")
    config_path: Path | None = Field(default=None, exclude=True)

    @field_validator("agents")
    @classmethod
    def validate_agent_profile_names(
        cls,
        value: dict[str, AgentProfileConfig],
    ) -> dict[str, AgentProfileConfig]:
        for name in value:
            if not name.strip():
                raise ValueError("agent profile names must not be empty")
            if name != name.strip():
                raise ValueError("agent profile names must not have surrounding whitespace")
        return value

    @model_validator(mode="after")
    def validate_config_shape(self) -> ContextEvalConfig:
        if self.agent is not None and self.agents:
            raise ValueError("cannot set both top-level agent and agents")
        if self.agent is None and not self.agents:
            raise ValueError("either agent or agents is required")
        if not self.variants:
            raise ValueError("at least one context variant is required")
        return self

    def uses_agent_profile_map(self) -> bool:
        return bool(self.agents)

    def agent_profiles(self) -> dict[str, AgentConfig]:
        if self.agents:
            return {
                name: profile.to_agent_config(name)
                for name, profile in self.agents.items()
            }
        if self.agent is not None:
            return {self.agent.name: self.agent}
        return {}

    def primary_agent(self) -> AgentConfig:
        profiles = self.agent_profiles()
        if not profiles:
            raise ValueError("no agent profiles configured")
        return next(iter(profiles.values()))


class ValidationConfig(BaseModel):
    commands: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = Field(default=None, ge=1)


class ExpectedOutcomeFile(BaseModel):
    path: str
    change_type: str = "modified"
    must_change: bool = False
    expected_snippets: list[str] = Field(default_factory=list)
    forbidden_snippets: list[str] = Field(default_factory=list)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return validate_repo_relative_path(value)


class ExpectedOutcomeConfig(BaseModel):
    summary: str | None = None
    files: list[ExpectedOutcomeFile] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    acceptance_points: list[str] = Field(default_factory=list)

    @field_validator("forbidden_paths")
    @classmethod
    def validate_forbidden_paths(cls, value: list[str]) -> list[str]:
        return _validate_repo_relative_paths(value)


class SnippetCheckConfig(BaseModel):
    path: str
    snippets: list[str] = Field(default_factory=list)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return validate_repo_relative_path(value)

    @field_validator("snippets")
    @classmethod
    def validate_snippets(cls, value: list[str]) -> list[str]:
        for snippet in value:
            if not snippet:
                raise ValueError("snippet must not be empty")
        return value


class HardEvaluationConfig(BaseModel):
    enabled: bool = True
    require_validation_pass: bool = False
    max_changed_files: int | None = Field(default=None, ge=0)
    required_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    expected_snippets: list[SnippetCheckConfig] = Field(default_factory=list)
    forbidden_snippets: list[SnippetCheckConfig] = Field(default_factory=list)
    min_insertions: int | None = Field(default=None, ge=0)
    max_insertions: int | None = Field(default=None, ge=0)
    min_deletions: int | None = Field(default=None, ge=0)
    max_deletions: int | None = Field(default=None, ge=0)

    @field_validator("required_paths", "forbidden_paths")
    @classmethod
    def validate_paths(cls, value: list[str]) -> list[str]:
        return _validate_repo_relative_paths(value)


class SoftRubricItem(BaseModel):
    name: str
    weight: float = Field(default=1, gt=0)
    description: str = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("rubric name must not be empty")
        return stripped


class SoftEvaluationConfig(BaseModel):
    enabled: bool = True
    mode: Literal["payload-only"] = "payload-only"
    max_score: float = Field(default=10, gt=0)
    rubric: list[SoftRubricItem] = Field(default_factory=list)


class TaskConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    prompt: str
    repo_ref: str | None = None
    title: str | None = None
    category: str | None = None
    difficulty: str | None = None
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    expected_outcome: ExpectedOutcomeConfig | None = None
    hard_evaluation: HardEvaluationConfig | None = None
    soft_evaluation: SoftEvaluationConfig | None = None

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
    reasoning_step_count: int | None = Field(default=None, ge=0)
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
    hard_evaluation_status: HardEvaluationStatus = "not_configured"
    hard_evaluation_score: int | None = Field(default=None, ge=0)
    hard_evaluation_max_score: int | None = Field(default=None, ge=0)
    hard_evaluation_passed_checks: int | None = Field(default=None, ge=0)
    hard_evaluation_failed_checks: int | None = Field(default=None, ge=0)
    hard_evaluation_path: str | None = None
    soft_evaluation_status: SoftEvaluationStatus = "not_configured"
    soft_evaluation_payload_path: str | None = None
    soft_evaluation_result_path: str | None = None
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
