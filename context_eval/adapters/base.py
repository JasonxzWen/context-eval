from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from context_eval.models import CommandResult, TaskConfig, TelemetryStatus


class TelemetryCollectionPreparation(BaseModel):
    template_variables: dict[str, str] = Field(default_factory=dict)
    environment: dict[str, str] = Field(default_factory=dict)


class TelemetryCollectionResult(BaseModel):
    status: TelemetryStatus = "unavailable"
    source: str = "none"
    error: str | None = None
    agent_duration_seconds: float | None = Field(default=None, ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    tool_call_count: int | None = Field(default=None, ge=0)
    tool_calls_by_name: dict[str, int] = Field(default_factory=dict)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("telemetry source must not be empty")
        return value

    @field_validator("tool_calls_by_name")
    @classmethod
    def validate_tool_calls_by_name(cls, value: dict[str, int]) -> dict[str, int]:
        for name, count in value.items():
            if not name.strip():
                raise ValueError("tool call names must not be empty")
            if count < 0:
                raise ValueError("tool call counts must be non-negative")
        return value


class TelemetryCollector(ABC):
    source = "custom"

    def prepare(
        self,
        *,
        workspace: Path,
        prompt_file: Path,
        task: TaskConfig,
        variant: str,
        output_dir: Path,
    ) -> TelemetryCollectionPreparation:
        """Prepare local template variables or environment for a case."""
        return TelemetryCollectionPreparation()

    @abstractmethod
    def collect(
        self,
        *,
        workspace: Path,
        prompt_file: Path,
        task: TaskConfig,
        variant: str,
        output_dir: Path,
        command_result: CommandResult,
    ) -> TelemetryCollectionResult:
        """Collect normalized telemetry after an agent command exits."""


class NoOpTelemetryCollector(TelemetryCollector):
    source = "none"

    def collect(
        self,
        *,
        workspace: Path,
        prompt_file: Path,
        task: TaskConfig,
        variant: str,
        output_dir: Path,
        command_result: CommandResult,
    ) -> TelemetryCollectionResult:
        return TelemetryCollectionResult(status="unavailable", source=self.source)


class AgentAdapter(ABC):
    @abstractmethod
    def run(
        self,
        *,
        workspace: Path,
        prompt: str,
        prompt_file: Path,
        task: TaskConfig,
        variant: str,
        output_dir: Path,
        timeout_seconds: int,
    ) -> CommandResult:
        """Run an agent against a prepared workspace."""

    @abstractmethod
    def collect_telemetry(
        self,
        *,
        workspace: Path,
        prompt_file: Path,
        task: TaskConfig,
        variant: str,
        output_dir: Path,
        command_result: CommandResult,
    ) -> TelemetryCollectionResult:
        """Collect normalized adapter telemetry for a completed command."""
