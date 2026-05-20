from __future__ import annotations

import json
import shlex
from collections import Counter
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
                "reasoning_step_count",
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

        return TelemetryCollectionResult(
            status="collected",
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
            "reasoning_step_count": cls._optional_nonnegative_int(
                data,
                "reasoning_step_count",
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


class CodexJsonlTelemetryCollector(TelemetryCollector):
    source = "codex-jsonl"

    def __init__(
        self,
        *,
        file: str = "codex-events.jsonl",
        final_message_file: str = "codex-final-message.md",
    ) -> None:
        self.file = file
        self.final_message_file = final_message_file

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
        output_dir.mkdir(parents=True, exist_ok=True)
        events_file = output_dir / self.file
        final_message_file = output_dir / self.final_message_file
        if command_result.stdout:
            events_file.parent.mkdir(parents=True, exist_ok=True)
            events_file.write_text(command_result.stdout, encoding="utf-8")

        if not events_file.exists():
            return TelemetryCollectionResult(
                status="unavailable",
                source=self.source,
                error=f"Codex JSONL events not found: {events_file}",
                telemetry_evidence_gaps=["codex_events_missing"],
            )

        raw_lines = events_file.read_text(encoding="utf-8", errors="replace").splitlines()
        lines = [line for line in raw_lines if line.strip()]
        if not lines:
            return TelemetryCollectionResult(
                status="unavailable",
                source=self.source,
                error=f"Codex JSONL events empty: {events_file}",
                codex_events_path=str(events_file),
                telemetry_evidence_gaps=["codex_events_empty"],
            )

        events: list[dict] = []
        errors: list[str] = []
        for line_number, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid Codex JSONL line {line_number}: {exc}")
                continue
            if not isinstance(event, dict):
                errors.append(f"invalid Codex JSONL line {line_number}: event must be an object")
                continue
            events.append(event)

        if errors and not events:
            return TelemetryCollectionResult(
                status="error",
                source=self.source,
                error="; ".join(errors),
                codex_events_path=str(events_file),
                telemetry_evidence_gaps=["codex_events_malformed"],
            )

        metrics = self._normalize_events(events)
        evidence_gaps: list[str] = []
        if errors:
            evidence_gaps.append("codex_events_malformed")
        if metrics["usage"] is None:
            evidence_gaps.append("codex_usage_missing")
        model_name = self._model_from_command(command_result.command)
        if model_name is None:
            model_name = self._model_from_events(events)
        if model_name is None:
            evidence_gaps.append("codex_model_missing")

        final_message_missing = not final_message_file.exists()
        if final_message_missing and metrics["last_agent_message"]:
            final_message_file.write_text(
                str(metrics["last_agent_message"]),
                encoding="utf-8",
            )
        elif final_message_missing:
            evidence_gaps.append("codex_final_message_missing")
        if final_message_missing and final_message_file.exists():
            evidence_gaps.append("codex_output_last_message_missing")

        status = "collected"
        if errors or metrics["usage"] is None:
            status = "partial" if events else "error"
        error_message = "; ".join(errors)
        if metrics["usage"] is None:
            error_message = "; ".join(
                item for item in [error_message, "missing turn.completed usage"] if item
            )

        usage = metrics["usage"] or {}
        prompt_tokens = self._optional_int(usage.get("input_tokens"))
        cached_input_tokens = self._optional_int(usage.get("cached_input_tokens"))
        completion_tokens = self._optional_int(usage.get("output_tokens"))
        reasoning_tokens = self._optional_int(usage.get("reasoning_output_tokens"))
        total_tokens = (
            prompt_tokens + completion_tokens
            if prompt_tokens is not None and completion_tokens is not None
            else None
        )

        return TelemetryCollectionResult(
            status=status,
            source=self.source,
            error=error_message or None,
            agent_duration_seconds=command_result.duration_seconds,
            prompt_tokens=prompt_tokens,
            cached_input_tokens=cached_input_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            reasoning_tokens=reasoning_tokens,
            tool_call_count=sum(metrics["tool_calls_by_name"].values())
            if metrics["tool_calls_by_name"]
            else 0,
            tool_calls_by_name=dict(sorted(metrics["tool_calls_by_name"].items())),
            command_call_count=metrics["command_call_count"],
            model_name=model_name,
            telemetry_evidence_gaps=evidence_gaps,
            codex_events_path=str(events_file),
            codex_final_message_path=str(final_message_file)
            if final_message_file.exists()
            else None,
            codex_error_reason=metrics["error_reason"],
        )

    @staticmethod
    def _normalize_events(events: list[dict]) -> dict[str, object]:
        tool_calls: Counter[str] = Counter()
        command_call_count = 0
        usage: dict | None = None
        last_agent_message: str | None = None
        error_reason: str | None = None

        for event in events:
            event_type = event.get("type")
            if event_type == "turn.completed" and isinstance(event.get("usage"), dict):
                usage = event["usage"]
            elif event_type == "turn.failed" and isinstance(event.get("error"), dict):
                error_reason = str(event["error"].get("message") or "")
            elif event_type == "error":
                error_reason = str(event.get("message") or "")

            item = event.get("item")
            if not isinstance(item, dict) or event_type != "item.completed":
                continue
            item_type = item.get("type")
            if item_type == "agent_message" and isinstance(item.get("text"), str):
                last_agent_message = item["text"]
            elif item_type == "command_execution":
                command_call_count += 1
                if item.get("status") == "failed" and item.get("command"):
                    error_reason = f"command failed: {item.get('command')}"
            elif item_type == "mcp_tool_call":
                server = str(item.get("server") or "mcp")
                tool = str(item.get("tool") or "unknown")
                tool_calls[f"mcp:{server}/{tool}"] += 1
                if item.get("error") and isinstance(item["error"], dict):
                    error_reason = str(item["error"].get("message") or error_reason or "")
            elif item_type == "collab_tool_call":
                tool_calls[f"collab:{item.get('tool') or 'unknown'}"] += 1
            elif item_type == "web_search":
                tool_calls["web_search"] += 1
            elif item_type == "file_change":
                tool_calls["file_change"] += 1

        return {
            "usage": usage,
            "tool_calls_by_name": tool_calls,
            "command_call_count": command_call_count,
            "last_agent_message": last_agent_message,
            "error_reason": error_reason or None,
        }

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        if value < 0:
            return None
        return value

    @staticmethod
    def _model_from_command(command: str) -> str | None:
        try:
            parts = shlex.split(command, posix=False)
        except ValueError:
            return None
        for index, part in enumerate(parts):
            stripped = part.strip("\"'")
            if stripped in {"--model", "-m"} and index + 1 < len(parts):
                return parts[index + 1].strip("\"'")
            if stripped.startswith("--model="):
                return stripped.split("=", 1)[1].strip("\"'")
        return None

    @staticmethod
    def _model_from_events(events: list[dict]) -> str | None:
        for event in events:
            for key in ["model", "model_name"]:
                value = event.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None


def build_telemetry_collector(config: AgentTelemetryConfig) -> TelemetryCollector:
    if config.collector == "none":
        return NoOpTelemetryCollector()
    if config.collector == "json-file":
        return JsonFileTelemetryCollector(
            file=config.file,
            environment_variable=config.environment_variable,
        )
    if config.collector == "codex-jsonl":
        file = "codex-events.jsonl" if config.file == "telemetry.json" else config.file
        return CodexJsonlTelemetryCollector(file=file)
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
