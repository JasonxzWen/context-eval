from pathlib import Path

import pytest
from pydantic import ValidationError

from context_eval.adapters.base import (
    NoOpTelemetryCollector,
    TelemetryCollectionPreparation,
    TelemetryCollectionResult,
    TelemetryCollector,
)
from context_eval.adapters.command import CommandTemplateAgent
from context_eval.models import AgentConfig, CommandResult, TaskConfig


def _command_result() -> CommandResult:
    return CommandResult(
        command="agent",
        cwd="/repo",
        exit_code=0,
        stdout="",
        stderr="",
        duration_seconds=0.1,
    )


def test_noop_telemetry_collector_returns_unavailable_result(tmp_path: Path) -> None:
    collector = NoOpTelemetryCollector()
    task = TaskConfig(id="task-1", prompt="Fix it.")
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "artifacts"
    prompt_file = tmp_path / "prompt.md"

    preparation = collector.prepare(
        workspace=workspace,
        prompt_file=prompt_file,
        task=task,
        variant="baseline",
        output_dir=output_dir,
    )
    result = collector.collect(
        workspace=workspace,
        prompt_file=prompt_file,
        task=task,
        variant="baseline",
        output_dir=output_dir,
        command_result=_command_result(),
    )

    assert preparation == TelemetryCollectionPreparation()
    assert result.status == "unavailable"
    assert result.source == "none"
    assert result.error is None
    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.total_tokens is None
    assert result.reasoning_tokens is None
    assert result.tool_call_count is None
    assert result.tool_calls_by_name == {}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", ""),
        ("prompt_tokens", -1),
        ("tool_calls_by_name", {"": 1}),
        ("tool_calls_by_name", {"read": -1}),
    ],
)
def test_telemetry_collection_result_rejects_invalid_values(
    field: str,
    value: object,
) -> None:
    kwargs = {"status": "collected", "source": "test", field: value}
    with pytest.raises(ValidationError):
        TelemetryCollectionResult(**kwargs)


def test_command_template_agent_defaults_to_noop_collector_and_preserves_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run_command(
        command: str,
        *,
        cwd: Path,
        timeout_seconds: int,
        shell: bool,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        captured.update(
            command=command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            shell=shell,
            env=env,
        )
        return CommandResult(
            command=command,
            cwd=str(cwd),
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_seconds=0.2,
        )

    monkeypatch.setattr("context_eval.adapters.command.run_command", fake_run_command)

    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "artifacts"
    prompt_file = tmp_path / "prompt.md"
    task = TaskConfig(id="task-1", prompt="Fix it.")
    agent = CommandTemplateAgent(
        AgentConfig(
            name="test-agent",
            command=(
                "agent --workspace {workspace} --prompt-file {prompt_file} "
                "--task {task_id} --variant {variant} --output {output_dir}"
            ),
        )
    )

    command_result = agent.run(
        workspace=workspace,
        prompt="Fix it.",
        prompt_file=prompt_file,
        task=task,
        variant="baseline",
        output_dir=output_dir,
        timeout_seconds=60,
    )
    telemetry = agent.collect_telemetry(
        workspace=workspace,
        prompt_file=prompt_file,
        task=task,
        variant="baseline",
        output_dir=output_dir,
        command_result=command_result,
    )

    assert captured == {
        "command": (
            f"agent --workspace {workspace} --prompt-file {prompt_file} "
            f"--task task-1 --variant baseline --output {output_dir}"
        ),
        "cwd": workspace,
        "timeout_seconds": 60,
        "shell": True,
        "env": None,
    }
    assert output_dir.exists()
    assert telemetry.status == "unavailable"
    assert telemetry.source == "none"


def test_command_template_agent_allows_collector_preparation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class TestCollector(TelemetryCollector):
        source = "test"

        def prepare(
            self,
            *,
            workspace: Path,
            prompt_file: Path,
            task: TaskConfig,
            variant: str,
            output_dir: Path,
        ) -> TelemetryCollectionPreparation:
            return TelemetryCollectionPreparation(
                template_variables={"telemetry_marker": "case-telemetry.json"},
                environment={"CONTEXT_EVAL_TELEMETRY": str(output_dir / "telemetry.json")},
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
            return TelemetryCollectionResult(
                status="collected",
                source=self.source,
                prompt_tokens=4,
                tool_call_count=1,
                tool_calls_by_name={"read": 1},
            )

    captured: dict[str, object] = {}

    def fake_run_command(
        command: str,
        *,
        cwd: Path,
        timeout_seconds: int,
        shell: bool,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        captured.update(command=command, env=env)
        return CommandResult(
            command=command,
            cwd=str(cwd),
            exit_code=0,
            duration_seconds=0.2,
        )

    monkeypatch.setattr("context_eval.adapters.command.run_command", fake_run_command)

    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "artifacts"
    task = TaskConfig(id="task-1", prompt="Fix it.")
    agent = CommandTemplateAgent(
        AgentConfig(name="test-agent", command="agent --telemetry {telemetry_marker}"),
        telemetry_collector=TestCollector(),
    )

    command_result = agent.run(
        workspace=workspace,
        prompt="Fix it.",
        prompt_file=tmp_path / "prompt.md",
        task=task,
        variant="baseline",
        output_dir=output_dir,
        timeout_seconds=60,
    )
    telemetry = agent.collect_telemetry(
        workspace=workspace,
        prompt_file=tmp_path / "prompt.md",
        task=task,
        variant="baseline",
        output_dir=output_dir,
        command_result=command_result,
    )

    assert captured == {
        "command": "agent --telemetry case-telemetry.json",
        "env": {"CONTEXT_EVAL_TELEMETRY": str(output_dir / "telemetry.json")},
    }
    assert telemetry.status == "collected"
    assert telemetry.source == "test"
    assert telemetry.prompt_tokens == 4
    assert telemetry.tool_calls_by_name == {"read": 1}
