import json

import pytest
from pydantic import ValidationError

from context_eval.models import CaseResult


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
