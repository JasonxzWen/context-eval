import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from context_eval.models import (
    AgentConfig,
    AgentProfileConfig,
    CaseResult,
    ContextEvalConfig,
    RepoConfig,
    VariantConfig,
    render_agent_command_preview,
    validate_agent_command_template,
)


def _case_result_kwargs() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "task_id": "task-1",
        "variant": "baseline",
        "repo_ref": "main",
        "agent_name": "agent",
        "network": "disabled",
        "status": "completed",
    }


def test_case_result_defaults_old_rows_to_unavailable_telemetry() -> None:
    old_row = json.dumps(_case_result_kwargs())

    result = CaseResult.model_validate_json(old_row)
    dumped = json.loads(result.model_dump_json())

    assert result.telemetry_status == "unavailable"
    assert result.telemetry_source == "none"
    assert result.telemetry_error is None
    assert result.agent_duration_seconds is None
    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.total_tokens is None
    assert result.reasoning_tokens is None
    assert result.tool_call_count is None
    assert result.tool_calls_by_name == {}
    assert dumped["telemetry_status"] == "unavailable"
    assert dumped["telemetry_source"] == "none"
    assert dumped["tool_calls_by_name"] == {}


def test_case_result_accepts_collected_telemetry() -> None:
    result = CaseResult(
        **_case_result_kwargs(),
        telemetry_status="collected",
        telemetry_source="json-file",
        agent_duration_seconds=1.25,
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        reasoning_tokens=5,
        tool_call_count=2,
        tool_calls_by_name={"read": 1, "write": 1},
    )

    assert result.telemetry_status == "collected"
    assert result.telemetry_source == "json-file"
    assert result.agent_duration_seconds == 1.25
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 20
    assert result.total_tokens == 30
    assert result.reasoning_tokens == 5
    assert result.tool_call_count == 2
    assert result.tool_calls_by_name == {"read": 1, "write": 1}


def test_case_result_accepts_partial_telemetry() -> None:
    result = CaseResult(
        **_case_result_kwargs(),
        telemetry_status="partial",
        telemetry_source="json-file",
        prompt_tokens=15,
        total_tokens=40,
    )

    assert result.telemetry_status == "partial"
    assert result.telemetry_source == "json-file"
    assert result.prompt_tokens == 15
    assert result.completion_tokens is None
    assert result.total_tokens == 40
    assert result.tool_call_count is None


def test_case_result_accepts_error_telemetry_state() -> None:
    result = CaseResult(
        **_case_result_kwargs(),
        telemetry_status="error",
        telemetry_source="json-file",
        telemetry_error="invalid telemetry JSON",
    )

    assert result.telemetry_status == "error"
    assert result.telemetry_source == "json-file"
    assert result.telemetry_error == "invalid telemetry JSON"
    assert result.prompt_tokens is None
    assert result.tool_calls_by_name == {}


@pytest.mark.parametrize("tool_calls_by_name", [{"": 1}, {"read": -1}])
def test_case_result_rejects_invalid_tool_call_counts(
    tool_calls_by_name: dict[str, int],
) -> None:
    with pytest.raises(ValidationError):
        CaseResult(
            **_case_result_kwargs(),
            telemetry_status="collected",
            telemetry_source="json-file",
            tool_calls_by_name=tool_calls_by_name,
        )


def test_context_config_exposes_legacy_agent_as_single_profile() -> None:
    config = ContextEvalConfig(
        repo=RepoConfig(path=Path("."), base_ref="HEAD"),
        agent=AgentConfig(
            name="legacy-agent",
            command="agent -p {prompt_file}",
            timeout_minutes=5,
        ),
        variants={"baseline": VariantConfig(description="Baseline")},
    )

    profiles = config.agent_profiles()

    assert list(profiles) == ["legacy-agent"]
    assert profiles["legacy-agent"].name == "legacy-agent"
    assert profiles["legacy-agent"].kind == "custom"
    assert config.primary_agent().name == "legacy-agent"
    assert config.uses_agent_profile_map() is False


def test_context_config_exposes_named_profiles_from_agents_map() -> None:
    config = ContextEvalConfig(
        repo=RepoConfig(path=Path("."), base_ref="HEAD"),
        agents={
            "codex": AgentProfileConfig(
                kind="codex-cli",
                command="codex exec -C {workspace} - < {prompt_file}",
            ),
            "coco": AgentProfileConfig(
                kind="custom",
                command="coco -p {prompt_file}",
                timeout_minutes=15,
            ),
            "trae": AgentProfileConfig(
                kind="traecli",
                command='traecli -p "{prompt}"',
                timeout_minutes=20,
            ),
        },
        variants={"baseline": VariantConfig(description="Baseline")},
    )

    profiles = config.agent_profiles()

    assert list(profiles) == ["codex", "coco", "trae"]
    assert profiles["codex"].name == "codex"
    assert profiles["codex"].kind == "codex-cli"
    assert profiles["coco"].name == "coco"
    assert profiles["coco"].timeout_minutes == 15
    assert profiles["trae"].kind == "traecli"
    assert profiles["trae"].command == 'traecli -p "{prompt}"'
    assert profiles["trae"].timeout_minutes == 20
    assert config.primary_agent().name == "codex"
    assert config.uses_agent_profile_map() is True


def test_agent_profile_rejects_unsupported_kind() -> None:
    with pytest.raises(ValidationError):
        AgentProfileConfig(kind="hosted-agent", command="agent -p {prompt_file}")


def test_agent_command_template_validator_rejects_unknown_variables() -> None:
    with pytest.raises(ValueError, match="unknown variable: missing"):
        validate_agent_command_template("agent -p {prompt_file} --bad {missing}")


def test_agent_command_preview_renders_supported_variables() -> None:
    preview = render_agent_command_preview(
        "coco -p {prompt_file} --task {task_id} --variant {variant} "
        "--out {output_dir} --telemetry {telemetry_file}",
        workspace=Path("workspace"),
        prompt="Fix it.",
        prompt_file=Path("prompt.md"),
        task_id="task-1",
        variant="baseline",
        output_dir=Path("artifacts"),
        telemetry_file=Path("artifacts/telemetry.json"),
    )

    assert preview == (
        "coco -p prompt.md --task task-1 --variant baseline "
        "--out artifacts --telemetry artifacts\\telemetry.json"
    )
