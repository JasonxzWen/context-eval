from __future__ import annotations

from pathlib import Path

from context_eval.adapters.base import (
    AgentAdapter,
    NoOpTelemetryCollector,
    TelemetryCollectionResult,
    TelemetryCollector,
)
from context_eval.logging import run_command
from context_eval.models import AgentConfig, CommandResult, TaskConfig


def render_command_template(template: str, variables: dict[str, str]) -> str:
    try:
        return template.format(**variables)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"agent command template references unknown variable: {missing}") from exc


class CommandTemplateAgent(AgentAdapter):
    def __init__(
        self,
        config: AgentConfig,
        telemetry_collector: TelemetryCollector | None = None,
    ) -> None:
        self.config = config
        self.telemetry_collector = telemetry_collector or NoOpTelemetryCollector()

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
