from __future__ import annotations

import json
from pathlib import Path

from context_eval.adapters.base import (
    AgentAdapter,
    NoOpTelemetryCollector,
    TelemetryCollectionPreparation,
    TelemetryCollectionResult,
    TelemetryCollector,
)
from context_eval.logging import run_command
from context_eval.models import (
    AgentConfig,
    AgentTelemetryConfig,
    CommandResult,
    TaskConfig,
    validate_agent_command_template,
)


def render_command_template(template: str, variables: dict[str, str]) -> str:
    validate_agent_command_template(template, allowed_variables=set(variables))
    try:
        return template.format(**variables)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"agent command template references unknown variable: {missing}") from exc


class JsonFileTelemetryCollector(TelemetryCollector):
    source = "json-file"

    def __init__(
        self,
        *,
        file: str = "telemetry.json",
        environment_variable: str | None = "CONTEXT_EVAL_TELEMETRY_FILE",
    ) -> None:
        self.config = AgentTelemetryConfig(
            collector="json-file",
            file=file,
            environment_variable=environment_variable,
        )

    def prepare(
        self,
        *,
        workspace: Path,
        prompt_file: Path,
        task: TaskConfig,
        variant: str,
        output_dir: Path,
    ) -> TelemetryCollectionPreparation:
        telemetry_file = self._telemetry_file(output_dir)
        telemetry_file.parent.mkdir(parents=True, exist_ok=True)
        environment = (
            {self.config.environment_variable: str(telemetry_file)}
            if self.config.environment_variable
            else {}
        )
        return TelemetryCollectionPreparation(
            template_variables={"telemetry_file": str(telemetry_file)},
            environment=environment,
        )

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
        telemetry_file = self._telemetry_file(output_dir)
        if not telemetry_file.exists():
            return TelemetryCollectionResult(
                status="unavailable",
                source=self.source,
                error=f"telemetry file not found: {telemetry_file}",
            )

        try:
            data = json.loads(telemetry_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return TelemetryCollectionResult(
                status="error",
                source=self.source,
                error=f"invalid telemetry JSON: {exc}",
            )

        if not isinstance(data, dict):
            return TelemetryCollectionResult(
                status="error",
                source=self.source,
                error="telemetry JSON root must be an object",
            )

        metrics, errors = self._normalize_metrics(data)
        has_metrics = any(
            metrics[field] is not None
            for field in [
                "agent_duration_seconds",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "reasoning_tokens",
                "tool_call_count",
            ]
        ) or bool(metrics["tool_calls_by_name"])

        if errors and not has_metrics:
            return TelemetryCollectionResult(
                status="error",
                source=self.source,
                error="; ".join(errors),
            )
        if errors:
            return TelemetryCollectionResult(
                status="partial",
                source=self.source,
                error="; ".join(errors),
                **metrics,
            )
        if not has_metrics:
            return TelemetryCollectionResult(
                status="unavailable",
                source=self.source,
                error="no recognized telemetry fields found",
            )

        complete = metrics["total_tokens"] is not None and metrics["tool_call_count"] is not None
        return TelemetryCollectionResult(
            status="collected" if complete else "partial",
            source=self.source,
            **metrics,
        )

    def _telemetry_file(self, output_dir: Path) -> Path:
        return output_dir / self.config.file

    @classmethod
    def _normalize_metrics(cls, data: dict) -> tuple[dict[str, object], list[str]]:
        errors: list[str] = []
        metrics: dict[str, object] = {
            "agent_duration_seconds": cls._optional_nonnegative_number(
                data,
                "agent_duration_seconds",
                errors,
            ),
            "prompt_tokens": cls._optional_nonnegative_int(data, "prompt_tokens", errors),
            "completion_tokens": cls._optional_nonnegative_int(
                data,
                "completion_tokens",
                errors,
            ),
            "total_tokens": cls._optional_nonnegative_int(data, "total_tokens", errors),
            "reasoning_tokens": cls._optional_nonnegative_int(
                data,
                "reasoning_tokens",
                errors,
            ),
            "tool_call_count": cls._optional_nonnegative_int(data, "tool_call_count", errors),
            "tool_calls_by_name": cls._tool_calls_by_name(data, errors),
        }
        if metrics["tool_call_count"] is None and metrics["tool_calls_by_name"]:
            metrics["tool_call_count"] = sum(metrics["tool_calls_by_name"].values())
        return metrics, errors

    @staticmethod
    def _optional_nonnegative_number(
        data: dict,
        field: str,
        errors: list[str],
    ) -> float | None:
        if field not in data:
            return None
        value = data[field]
        if isinstance(value, bool) or not isinstance(value, int | float):
            errors.append(f"{field} must be a non-negative number")
            return None
        if value < 0:
            errors.append(f"{field} must be a non-negative number")
            return None
        return float(value)

    @staticmethod
    def _optional_nonnegative_int(
        data: dict,
        field: str,
        errors: list[str],
    ) -> int | None:
        if field not in data:
            return None
        value = data[field]
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{field} must be a non-negative integer")
            return None
        if value < 0:
            errors.append(f"{field} must be a non-negative integer")
            return None
        return value

    @staticmethod
    def _tool_calls_by_name(data: dict, errors: list[str]) -> dict[str, int]:
        if "tool_calls_by_name" not in data:
            return {}
        value = data["tool_calls_by_name"]
        if not isinstance(value, dict):
            errors.append("tool_calls_by_name must be an object")
            return {}

        calls: dict[str, int] = {}
        for raw_name, raw_count in value.items():
            if not isinstance(raw_name, str) or not raw_name.strip():
                errors.append("tool call names must not be empty")
                continue
            if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
                errors.append(f"tool call count for {raw_name!r} must be a non-negative integer")
                continue
            calls[raw_name.strip()] = raw_count
        return calls


def build_telemetry_collector(config: AgentTelemetryConfig) -> TelemetryCollector:
    if config.collector == "none":
        return NoOpTelemetryCollector()
    if config.collector == "json-file":
        return JsonFileTelemetryCollector(
            file=config.file,
            environment_variable=config.environment_variable,
        )
    raise ValueError(f"unsupported telemetry collector: {config.collector}")


class CommandTemplateAgent(AgentAdapter):
    def __init__(
        self,
        config: AgentConfig,
        telemetry_collector: TelemetryCollector | None = None,
    ) -> None:
        self.config = config
        self.telemetry_collector = telemetry_collector or build_telemetry_collector(
            config.telemetry
        )

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
        output_dir.mkdir(parents=True, exist_ok=True)
        preparation = self.telemetry_collector.prepare(
            workspace=workspace,
            prompt_file=prompt_file,
            task=task,
            variant=variant,
            output_dir=output_dir,
        )
        command = render_command_template(
            self.config.command,
            {
                "workspace": str(workspace),
                "prompt": prompt,
                "prompt_file": str(prompt_file),
                "task_id": task.id,
                "variant": variant,
                "output_dir": str(output_dir),
                **preparation.template_variables,
            },
        )
        env = preparation.environment or None
        return run_command(
            command,
            cwd=workspace,
            timeout_seconds=timeout_seconds,
            shell=True,
            env=env,
        )

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
        return self.telemetry_collector.collect(
            workspace=workspace,
            prompt_file=prompt_file,
            task=task,
            variant=variant,
            output_dir=output_dir,
            command_result=command_result,
        )
