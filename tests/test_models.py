import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from context_eval.models import (
    AgentConfig,
    AgentProfileConfig,
    CaseResult,
    ContextEvalConfig,
    HardEvaluationConfig,
    RepoConfig,
    SoftEvaluationConfig,
    TaskConfig,
    TaskFile,
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
                kind="coco",
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
    assert profiles["coco"].kind == "coco"
    assert profiles["coco"].timeout_minutes == 15
    assert profiles["trae"].kind == "traecli"
    assert profiles["trae"].command == 'traecli -p "{prompt}"'
    assert profiles["trae"].timeout_minutes == 20
    assert config.primary_agent().name == "codex"
    assert config.uses_agent_profile_map() is True


def test_agent_profile_rejects_unsupported_kind() -> None:
    with pytest.raises(ValidationError):
        AgentProfileConfig(kind="hosted-agent", command="agent -p {prompt_file}")


def test_old_task_model_remains_valid_without_hybrid_evaluation() -> None:
    task_file = TaskFile.model_validate(
        {"tasks": [{"id": "task-1", "prompt": "Fix the bug.", "x_keep": "value"}]}
    )

    task = task_file.tasks[0]

    assert task.expected_outcome is None
    assert task.hard_evaluation is None
    assert task.soft_evaluation is None
    assert task.model_extra == {"x_keep": "value"}


def test_task_model_accepts_expected_outcome_hard_and_soft_evaluation() -> None:
    task = TaskConfig.model_validate(
        {
            "id": "mail-expire-attachment",
            "prompt": "Fix expired attachment claims.",
            "expected_outcome": {
                "summary": "Expired attachments cannot be claimed.",
                "files": [
                    {
                        "path": "src/mail/attachment.py",
                        "change_type": "modified",
                        "must_change": True,
                        "expected_snippets": ["expires_at"],
                        "forbidden_snippets": ["TODO"],
                    }
                ],
                "forbidden_paths": ["README.md"],
                "acceptance_points": ["Expired attachments fail."],
            },
            "hard_evaluation": {
                "enabled": True,
                "require_validation_pass": True,
                "max_changed_files": 5,
                "required_paths": ["src/mail/attachment.py"],
                "forbidden_paths": ["README.md"],
                "expected_snippets": [
                    {"path": "src/mail/attachment.py", "snippets": ["expires_at"]}
                ],
                "forbidden_snippets": [
                    {"path": "src/mail/attachment.py", "snippets": ["TODO"]}
                ],
                "command_checks": [
                    {
                        "label": "targeted-test",
                        "command": "python -m pytest tests/test_mail.py",
                        "expected": "passed",
                    }
                ],
            },
            "soft_evaluation": {
                "enabled": True,
                "mode": "payload-only",
                "max_score": 10,
                "rubric": [
                    {
                        "name": "requirement_match",
                        "weight": 4,
                        "description": "Patch satisfies the requested behavior.",
                    }
                ],
            },
        }
    )

    assert task.expected_outcome is not None
    assert task.expected_outcome.files[0].path == "src/mail/attachment.py"
    assert task.hard_evaluation is not None
    assert isinstance(task.hard_evaluation, HardEvaluationConfig)
    assert task.hard_evaluation.require_validation_pass is True
    assert task.hard_evaluation.required_paths == ["src/mail/attachment.py"]
    assert task.hard_evaluation.expected_snippets[0].snippets == ["expires_at"]
    assert task.hard_evaluation.command_checks[0].label == "targeted-test"
    assert task.hard_evaluation.command_checks[0].timeout_seconds == 60
    assert task.soft_evaluation is not None
    assert isinstance(task.soft_evaluation, SoftEvaluationConfig)
    assert task.soft_evaluation.mode == "payload-only"
    assert task.soft_evaluation.max_score == 10
    assert task.soft_evaluation.rubric[0].name == "requirement_match"


@pytest.mark.parametrize(
    "payload",
    [
        {"expected_outcome": {"files": [{"path": "../escape.py"}]}},
        {"expected_outcome": {"forbidden_paths": ["C:/repo/README.md"]}},
        {"hard_evaluation": {"required_paths": ["/abs/path.py"]}},
        {"hard_evaluation": {"expected_snippets": [{"path": "../x.py", "snippets": ["x"]}]}},
    ],
)
def test_task_model_rejects_unsafe_expected_paths(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="safe repository-relative path"):
        TaskConfig.model_validate(
            {
                "id": "task-1",
                "prompt": "Fix the bug.",
                **payload,
            }
        )


def test_agent_command_template_validator_rejects_unknown_variables() -> None:
    with pytest.raises(ValueError, match="unknown variable: missing"):
        validate_agent_command_template("agent -p {prompt_file} --bad {missing}")


def test_agent_command_preview_renders_supported_variables() -> None:
    telemetry_file = Path("artifacts") / "telemetry.json"
    preview = render_agent_command_preview(
        "coco -p {prompt_file} --task {task_id} --variant {variant} "
        "--out {output_dir} --telemetry {telemetry_file}",
        workspace=Path("workspace"),
        prompt="Fix it.",
        prompt_file=Path("prompt.md"),
        task_id="task-1",
        variant="baseline",
        output_dir=Path("artifacts"),
        telemetry_file=telemetry_file,
    )

    assert preview == (
        "coco -p prompt.md --task task-1 --variant baseline "
        f"--out artifacts --telemetry {telemetry_file}"
    )
