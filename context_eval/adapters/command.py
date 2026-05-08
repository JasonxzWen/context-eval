from __future__ import annotations

from pathlib import Path

from context_eval.adapters.base import AgentAdapter
from context_eval.logging import run_command
from context_eval.models import AgentConfig, CommandResult, TaskConfig


def render_command_template(template: str, variables: dict[str, str]) -> str:
    try:
        return template.format(**variables)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"agent command template references unknown variable: {missing}") from exc


class CommandTemplateAgent(AgentAdapter):
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

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
        command = render_command_template(
            self.config.command,
            {
                "workspace": str(workspace),
                "prompt": prompt,
                "prompt_file": str(prompt_file),
                "task_id": task.id,
                "variant": variant,
                "output_dir": str(output_dir),
            },
        )
        return run_command(command, cwd=workspace, timeout_seconds=timeout_seconds, shell=True)
