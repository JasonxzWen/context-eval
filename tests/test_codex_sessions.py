from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from context_eval.adapters.command import CodexJsonlTelemetryCollector
from context_eval.cli import app
from context_eval.codex_sessions import summarize_codex_sessions
from context_eval.models import CommandResult, TaskConfig

FIXTURES = Path(__file__).parent / "fixtures" / "codex-sessions"
SENSITIVE_STRINGS = [
    "SECRET_TASK_STARTED_MESSAGE",
    "SECRET_TOOL_ARGUMENT",
    "SECRET_TOOL_OUTPUT",
    "SECRET_USER_PROMPT",
    "SECRET_ASSISTANT_MESSAGE",
    "SECRET_ROLLBACK_MESSAGE",
    "SECRET_REASONING",
    "SECRET_ENCRYPTED_REASONING",
    "SECRET_CUSTOM_TOOL_ARGUMENT",
    "SECRET_CUSTOM_TOOL_OUTPUT",
    "SECRET_TASK_COMPLETE_MESSAGE",
    "SECRET_UNKNOWN_CONTENT",
]


def test_codex_session_parser_counts_rows_payloads_and_malformed_lines() -> None:
    summary = summarize_codex_sessions([FIXTURES / "session-a.jsonl"])
    session = summary.sessions[0]

    assert summary.total_files == 1
    assert summary.total_events == 9
    assert summary.total_turns == 1
    assert summary.malformed_line_count == 1
    assert session.row_type_counts == {
        "event_msg": 2,
        "response_item": 5,
        "session_meta": 1,
        "turn_context": 1,
    }
    assert session.payload_type_counts == {
        "agent_message": 1,
        "function_call": 1,
        "function_call_output": 1,
        "message": 1,
        "task_started": 1,
        "thread_rolled_back": 1,
        "token_count": 1,
    }
    assert session.first_timestamp == "2026-05-27T01:00:00Z"
    assert session.last_timestamp == "2026-05-27T01:00:08Z"
    assert session.byte_size > 0


def test_codex_session_parser_normalizes_tokens_and_tool_counts() -> None:
    summary = summarize_codex_sessions(
        [FIXTURES / "session-b.jsonl", FIXTURES / "session-a.jsonl"]
    )

    assert [Path(session.path).name for session in summary.sessions] == [
        "session-a.jsonl",
        "session-b.jsonl",
    ]
    assert summary.token_observation_count == 2
    assert summary.latest_token_usage == {
        "cached_input_tokens": 25,
        "input_tokens": 150,
        "output_tokens": 40,
        "reasoning_output_tokens": 9,
        "total_tokens": 190,
    }
    assert summary.max_token_usage == {
        "cached_input_tokens": 25,
        "input_tokens": 150,
        "output_tokens": 40,
        "reasoning_output_tokens": 9,
        "total_tokens": 190,
    }
    assert summary.call_counts_by_name == {"shell_command": 1, "view_image": 1}
    assert summary.call_counts_by_type == {"custom_tool_call": 1, "function_call": 1}
    assert summary.output_status_counts == {"failed": 1, "success": 1}
    assert summary.rate_limit_observation_count == 2
    assert summary.diagnostic_signal_counts == {
        "malformed_line": 1,
        "non_success_status": 2,
        "rate_limit_reached": 1,
        "thread_rolled_back": 1,
    }
    assert summary.sessions[1].payload_type_counts["future_payload"] == 1


def test_codex_session_summary_ranks_large_and_diagnostic_sessions() -> None:
    summary = summarize_codex_sessions([FIXTURES / "session-a.jsonl", FIXTURES / "session-b.jsonl"])

    assert summary.top_sessions_by_size
    assert summary.top_sessions_by_diagnostic_signal
    assert summary.top_sessions_by_diagnostic_signal[0]["diagnostic_signal_count"] == 3
    assert Path(summary.top_sessions_by_diagnostic_signal[0]["path"]).name == "session-a.jsonl"


def test_codex_session_summary_json_is_deterministic_and_content_safe() -> None:
    summary = summarize_codex_sessions([FIXTURES / "session-a.jsonl", FIXTURES / "session-b.jsonl"])
    payload = summary.to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["total_files"] == 2
    assert payload["latest_token_usage"]["total_tokens"] == 190
    assert payload["sessions"][0]["row_type_counts"] == {
        "event_msg": 2,
        "response_item": 5,
        "session_meta": 1,
        "turn_context": 1,
    }
    for sensitive in SENSITIVE_STRINGS:
        assert sensitive not in encoded
    for raw_field in [
        '"arguments":',
        '"content":',
        '"encrypted_content":',
        '"output":',
        '"summary":',
    ]:
        assert raw_field not in encoded


def test_codex_session_summary_cli_text_and_json_outputs_are_content_safe() -> None:
    text_result = CliRunner().invoke(
        app,
        [
            "codex-session-summary",
            str(FIXTURES / "session-a.jsonl"),
            str(FIXTURES / "session-b.jsonl"),
        ],
    )
    json_result = CliRunner().invoke(
        app,
        [
            "codex-session-summary",
            str(FIXTURES / "*.jsonl"),
            "--format",
            "json",
        ],
    )

    assert text_result.exit_code == 0
    assert "Codex session diagnostics" in text_result.output
    assert "Sessions: 2" in text_result.output
    assert "Turns: 2" in text_result.output
    assert "Token observations: 2" in text_result.output
    assert "shell_command=1" in text_result.output
    assert "view_image=1" in text_result.output
    assert "rate_limit_observations=2" in text_result.output
    assert "malformed_lines=1" in text_result.output

    assert json_result.exit_code == 0
    payload = json.loads(json_result.output)
    assert payload["total_files"] == 2
    assert payload["call_counts_by_name"] == {"shell_command": 1, "view_image": 1}
    assert payload["output_status_counts"] == {"failed": 1, "success": 1}
    assert payload["max_token_usage"]["total_tokens"] == 190

    combined = text_result.output + json_result.output
    for sensitive in SENSITIVE_STRINGS:
        assert sensitive not in combined


def test_codex_session_summary_cli_rejects_missing_inputs(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["codex-session-summary", str(tmp_path / "missing" / "*.jsonl")],
    )

    assert result.exit_code == 1
    assert "no Codex session files matched" in result.output


def test_codex_session_summary_cli_rejects_unknown_format() -> None:
    result = CliRunner().invoke(
        app,
        ["codex-session-summary", str(FIXTURES / "session-a.jsonl"), "--format", "csv"],
    )

    assert result.exit_code == 1
    assert "unsupported Codex session summary format" in result.output


def test_inspect_run_still_does_not_treat_sessions_as_run_artifacts(tmp_path: Path) -> None:
    session_dir = tmp_path / ".codex" / "sessions"
    session_dir.mkdir(parents=True)
    (session_dir / "session.jsonl").write_text(
        (FIXTURES / "session-a.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["inspect-run", str(session_dir)])

    assert result.exit_code == 1
    assert "results file not found" in result.output


def test_codex_jsonl_collector_stays_case_local(tmp_path: Path) -> None:
    global_session_dir = tmp_path / ".codex" / "sessions"
    global_session_dir.mkdir(parents=True)
    (global_session_dir / "session.jsonl").write_text(
        (FIXTURES / "session-a.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    collector = CodexJsonlTelemetryCollector()
    result = collector.collect(
        workspace=tmp_path,
        prompt_file=tmp_path / "prompt.md",
        task=TaskConfig(id="task", prompt="Run task."),
        variant="baseline",
        output_dir=tmp_path / "case-artifacts",
        command_result=CommandResult(
            command="codex exec --json",
            cwd=str(tmp_path),
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=0.1,
            timeout=False,
        ),
    )

    assert result.status == "unavailable"
    assert result.source == "codex-jsonl"
    assert result.telemetry_evidence_gaps == ["codex_events_missing"]
