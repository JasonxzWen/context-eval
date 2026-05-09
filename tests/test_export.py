import json
from pathlib import Path

from context_eval.export import export_run_csv, export_run_json
from context_eval.models import CaseResult


def _write_run(run_dir: Path, results: list[CaseResult]) -> None:
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "agent": {"name": "metadata-agent"},
                "repo": {"path": "repo", "base_ref": "main"},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )


def test_export_run_csv_is_deterministic_and_preserves_missing_telemetry(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    _write_run(
        run_dir,
        [
            CaseResult(
                run_id="run-1",
                case_id="task-b__experiment__trial-2",
                task_id="task-b",
                variant="experiment",
                trial_index=2,
                repo_ref="main",
                agent_name="agent-b",
                network="disabled",
                status="timeout",
                validation_status="failed",
                confidence="medium",
                duration_seconds=5.0,
            ),
            CaseResult(
                run_id="run-1",
                case_id="task-a__baseline__trial-1",
                task_id="task-a",
                variant="baseline",
                trial_index=1,
                repo_ref="main",
                agent_name="agent-a",
                network="disabled",
                status="completed",
                validation_status="passed",
                confidence="high",
                duration_seconds=3.0,
                agent_duration_seconds=2.5,
                telemetry_status="collected",
                telemetry_source="json-file",
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                reasoning_tokens=4,
                tool_call_count=2,
                tool_calls_by_name={"write": 1, "read": 1},
            ),
        ],
    )

    csv_text = export_run_csv(run_dir)

    lines = csv_text.splitlines()
    assert lines[0] == (
        "run_id,case_id,agent_name,task_id,variant,trial_index,status,"
        "validation_status,confidence,duration_seconds,agent_duration_seconds,"
        "prompt_tokens,completion_tokens,total_tokens,reasoning_tokens,"
        "tool_call_count,tool_calls_by_name"
    )
    assert lines[1] == (
        'run-1,task-a__baseline__trial-1,agent-a,task-a,baseline,1,completed,'
        'passed,high,3.00,2.50,10,20,30,4,2,"{""read"":1,""write"":1}"'
    )
    assert lines[2] == (
        'run-1,task-b__experiment__trial-2,agent-b,task-b,experiment,2,timeout,'
        "failed,medium,5.00,,,,,,,"
    )


def test_export_run_json_contains_sorted_cases_and_agent_summaries(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_run(
        run_dir,
        [
            CaseResult(
                run_id="run-1",
                case_id="task-a__baseline__trial-2",
                task_id="task-a",
                variant="baseline",
                trial_index=2,
                repo_ref="main",
                agent_name="agent-a",
                network="disabled",
                status="validation_failed",
                validation_status="failed",
                confidence="medium",
                duration_seconds=4.0,
                total_tokens=50,
                tool_call_count=3,
                telemetry_status="partial",
                telemetry_source="json-file",
            ),
            CaseResult(
                run_id="run-1",
                case_id="task-a__baseline__trial-1",
                task_id="task-a",
                variant="baseline",
                trial_index=1,
                repo_ref="main",
                agent_name="agent-a",
                network="disabled",
                status="completed",
                validation_status="passed",
                confidence="high",
                duration_seconds=2.0,
                agent_duration_seconds=1.5,
                telemetry_status="collected",
                telemetry_source="json-file",
                total_tokens=30,
                tool_call_count=1,
                tool_calls_by_name={"edit": 1},
            ),
            CaseResult(
                run_id="run-1",
                case_id="task-a__baseline__trial-1",
                task_id="task-a",
                variant="baseline",
                trial_index=1,
                repo_ref="main",
                agent_name="agent-b",
                network="disabled",
                status="completed",
                validation_status="passed",
                confidence="high",
                duration_seconds=8.0,
            ),
        ],
    )

    payload = json.loads(export_run_json(run_dir))

    assert payload["run"]["run_id"] == "run-1"
    assert [case["agent_name"] for case in payload["cases"]] == [
        "agent-a",
        "agent-a",
        "agent-b",
    ]
    assert payload["cases"][0]["trial_index"] == 1
    assert payload["cases"][0]["agent_duration_seconds"] == 1.5
    assert payload["cases"][2]["total_tokens"] is None
    assert payload["cases"][2]["tool_calls_by_name"] == {}
    assert payload["agent_summaries"] == [
        {
            "agent_name": "agent-a",
            "cases": 2,
            "pass_rate": 0.5,
            "avg_duration_seconds": 3.0,
            "avg_agent_duration_seconds": 1.5,
            "avg_total_tokens": 40,
            "avg_tool_call_count": 2,
            "telemetry_statuses": {"collected": 1, "partial": 1},
            "common_tool_names": ["edit"],
        },
        {
            "agent_name": "agent-b",
            "cases": 1,
            "pass_rate": 1.0,
            "avg_duration_seconds": 8.0,
            "avg_agent_duration_seconds": None,
            "avg_total_tokens": None,
            "avg_tool_call_count": None,
            "telemetry_statuses": {"unavailable": 1},
            "common_tool_names": [],
        },
    ]
