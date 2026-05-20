import csv
import json
from datetime import UTC, datetime
from io import StringIO
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
                telemetry_error="telemetry file not found: artifacts/telemetry.json",
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
                telemetry_source="codex-jsonl",
                prompt_tokens=10,
                cached_input_tokens=5,
                completion_tokens=20,
                total_tokens=30,
                reasoning_tokens=4,
                tool_call_count=2,
                command_call_count=1,
                tool_calls_by_name={"write": 1, "read": 1},
                model_name="gpt-5.4",
                provider_name="openai",
                codex_events_path="artifacts/task-a__baseline__trial-1/codex-events.jsonl",
                codex_final_message_path=(
                    "artifacts/task-a__baseline__trial-1/codex-final-message.md"
                ),
            ),
        ],
    )

    csv_text = export_run_csv(run_dir)

    lines = csv_text.splitlines()
    assert lines[0] == (
        "run_id,case_id,agent_name,task_id,variant,trial_index,status,"
        "validation_status,confidence,telemetry_status,telemetry_source,telemetry_error,"
        "duration_seconds,agent_duration_seconds,"
        "prompt_tokens,cached_input_tokens,completion_tokens,total_tokens,reasoning_tokens,"
        "tool_call_count,command_call_count,tool_calls_by_name,reasoning_step_count,"
        "model_name,provider_name,telemetry_evidence_gaps,codex_events_path,"
        "codex_final_message_path,codex_error_reason,"
        "hard_evaluation_status,hard_evaluation_score,hard_evaluation_max_score,"
        "hard_evaluation_passed_checks,hard_evaluation_failed_checks,"
        "soft_evaluation_status,changed_files,insertions,deletions,touched_paths"
    )
    rows = list(csv.DictReader(StringIO(csv_text)))
    assert [row["case_id"] for row in rows] == [
        "task-a__baseline__trial-1",
        "task-b__experiment__trial-2",
    ]
    assert rows[0]["telemetry_source"] == "codex-jsonl"
    assert rows[0]["cached_input_tokens"] == "5"
    assert rows[0]["command_call_count"] == "1"
    assert rows[0]["model_name"] == "gpt-5.4"
    assert rows[0]["provider_name"] == "openai"
    assert rows[0]["telemetry_evidence_gaps"] == ""
    assert rows[0]["codex_events_path"] == "artifacts/task-a__baseline__trial-1/codex-events.jsonl"
    assert (
        rows[0]["codex_final_message_path"]
        == "artifacts/task-a__baseline__trial-1/codex-final-message.md"
    )
    assert rows[0]["codex_error_reason"] == ""
    assert rows[1]["cached_input_tokens"] == ""
    assert rows[1]["command_call_count"] == ""
    assert rows[1]["model_name"] == ""


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
                command_call_count=2,
                telemetry_status="partial",
                telemetry_source="codex-jsonl",
                telemetry_error="completion_tokens must be a non-negative integer",
                telemetry_evidence_gaps=["codex_usage_missing"],
                codex_error_reason="usage event missing",
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
                cached_input_tokens=4,
                total_tokens=30,
                tool_call_count=1,
                command_call_count=1,
                tool_calls_by_name={"edit": 1},
                model_name="gpt-5.4",
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

    payload = json.loads(
        export_run_json(
            run_dir,
            exported_at=datetime(2026, 5, 11, 5, 30, tzinfo=UTC),
        )
    )

    assert payload["export_schema_version"] == "2"
    assert payload["exported_at"] == "2026-05-11T05:30:00Z"
    assert payload["source_files"] == ["results.jsonl", "run_metadata.json"]
    assert payload["case_count"] == 3
    assert payload["agent_count"] == 2
    assert payload["variant_count"] == 1
    assert payload["task_count"] == 1
    assert (
        payload["evaluation_explanation"]["hard_evaluation"]["score_meaning"]
        == "hard score 是通过检查数 / 可评分检查数，不是综合质量分。"
    )
    assert payload["evaluation_explanation"]["soft_evaluation"]["mode"] == "payload-only"
    assert payload["run"]["run_id"] == "run-1"
    assert [case["agent_name"] for case in payload["cases"]] == [
        "agent-a",
        "agent-a",
        "agent-b",
    ]
    assert payload["cases"][0]["trial_index"] == 1
    assert payload["cases"][0]["agent_duration_seconds"] == 1.5
    assert payload["cases"][0]["cached_input_tokens"] == 4
    assert payload["cases"][0]["command_call_count"] == 1
    assert payload["cases"][0]["model_name"] == "gpt-5.4"
    assert payload["cases"][0]["telemetry_evidence_gaps"] == []
    assert payload["cases"][0]["hard_evaluation_status"] == "not_configured"
    assert payload["cases"][0]["soft_evaluation_status"] == "not_configured"
    assert payload["cases"][1]["telemetry_status"] == "partial"
    assert payload["cases"][1]["telemetry_source"] == "codex-jsonl"
    assert (
        payload["cases"][1]["telemetry_error"]
        == "completion_tokens must be a non-negative integer"
    )
    assert payload["cases"][1]["command_call_count"] == 2
    assert payload["cases"][1]["telemetry_evidence_gaps"] == ["codex_usage_missing"]
    assert payload["cases"][1]["codex_error_reason"] == "usage event missing"
    assert payload["cases"][2]["total_tokens"] is None
    assert payload["cases"][2]["telemetry_status"] == "unavailable"
    assert payload["cases"][2]["telemetry_source"] == "none"
    assert payload["cases"][2]["telemetry_error"] is None
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
            "avg_command_call_count": 1.5,
            "telemetry_statuses": {"collected": 1, "partial": 1},
            "common_tool_names": ["edit"],
            "common_model_names": ["gpt-5.4"],
        },
        {
            "agent_name": "agent-b",
            "cases": 1,
            "pass_rate": 1.0,
            "avg_duration_seconds": 8.0,
            "avg_agent_duration_seconds": None,
            "avg_total_tokens": None,
            "avg_tool_call_count": None,
            "avg_command_call_count": None,
            "telemetry_statuses": {"unavailable": 1},
            "common_tool_names": [],
            "common_model_names": [],
        },
    ]


def test_export_run_json_contains_hard_and_soft_evaluation_fields(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_run(
        run_dir,
        [
            CaseResult(
                run_id="run-1",
                case_id="task-a__baseline",
                task_id="task-a",
                variant="baseline",
                repo_ref="main",
                agent_name="coco",
                network="disabled",
                status="completed",
                validation_status="passed",
                confidence="high",
                hard_evaluation_status="passed",
                hard_evaluation_score=4,
                hard_evaluation_max_score=4,
                hard_evaluation_passed_checks=4,
                hard_evaluation_failed_checks=0,
                hard_evaluation_path="artifacts/task-a__baseline/hard_evaluation.json",
                soft_evaluation_status="payload_generated",
                soft_evaluation_payload_path=(
                    "artifacts/task-a__baseline/soft_evaluation_payload.json"
                ),
                changed_files=1,
                touched_paths=["README.md"],
                reasoning_step_count=12,
            ),
        ],
    )

    payload = json.loads(
        export_run_json(
            run_dir,
            exported_at=datetime(2026, 5, 14, 5, 30, tzinfo=UTC),
        )
    )
    case = payload["cases"][0]

    assert case["hard_evaluation_status"] == "passed"
    assert case["hard_evaluation_score"] == 4
    assert case["hard_evaluation_max_score"] == 4
    assert case["hard_evaluation_path"].endswith("hard_evaluation.json")
    assert case["soft_evaluation_status"] == "payload_generated"
    assert case["soft_evaluation_payload_path"].endswith("soft_evaluation_payload.json")
    assert case["changed_files"] == 1
    assert case["touched_paths"] == ["README.md"]
    assert case["reasoning_step_count"] == 12


def test_export_run_json_includes_manual_reviews(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_run(
        run_dir,
        [
            CaseResult(
                run_id="run-1",
                case_id="task-a__baseline",
                task_id="task-a",
                variant="baseline",
                repo_ref="main",
                agent_name="coco",
                network="disabled",
                status="completed",
                validation_status="passed",
                confidence="high",
            ),
        ],
    )
    (run_dir / "manual_reviews.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "reviews": {
                    "task-a__baseline": {
                        "case_id": "task-a__baseline",
                        "decision": "pass",
                        "confidence": "high",
                        "reviewer": "manual",
                        "notes": "Accepted.",
                        "updated_at": "2026-05-19T16:30:00Z",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    payload = json.loads(
        export_run_json(
            run_dir,
            exported_at=datetime(2026, 5, 19, 8, 30, tzinfo=UTC),
        )
    )

    assert payload["source_files"] == [
        "results.jsonl",
        "run_metadata.json",
        "manual_reviews.json",
    ]
    assert payload["manual_reviews"]["reviews"]["task-a__baseline"]["decision"] == "pass"
    assert payload["cases"][0]["manual_review"] == {
        "case_id": "task-a__baseline",
        "decision": "pass",
        "confidence": "high",
        "reviewer": "manual",
        "notes": "Accepted.",
        "updated_at": "2026-05-19T16:30:00Z",
    }


def test_export_run_json_metadata_handles_missing_run_metadata(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-without-metadata"
    run_dir.mkdir()
    results = [
        CaseResult(
            run_id="run-from-results",
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
            duration_seconds=1.0,
        ),
        CaseResult(
            run_id="run-from-results",
            case_id="task-b__experiment__trial-1",
            task_id="task-b",
            variant="experiment",
            trial_index=1,
            repo_ref="main",
            agent_name="agent-b",
            network="disabled",
            status="timeout",
            validation_status="failed",
            confidence="low",
            duration_seconds=2.0,
        ),
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )

    payload = json.loads(
        export_run_json(
            run_dir,
            exported_at=datetime(2026, 5, 11, 5, 31, tzinfo=UTC),
        )
    )

    assert payload["exported_at"] == "2026-05-11T05:31:00Z"
    assert payload["source_files"] == ["results.jsonl"]
    assert payload["run"] == {
        "metadata": {},
        "run_id": "run-from-results",
    }
    assert payload["case_count"] == 2
    assert payload["agent_count"] == 2
    assert payload["variant_count"] == 2
    assert payload["task_count"] == 2


def test_export_run_json_metadata_handles_empty_results(tmp_path: Path) -> None:
    run_dir = tmp_path / "empty-run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text('{"run_id": "empty-run"}', encoding="utf-8")
    (run_dir / "results.jsonl").write_text("", encoding="utf-8")

    payload = json.loads(
        export_run_json(
            run_dir,
            exported_at=datetime(2026, 5, 11, 5, 32, tzinfo=UTC),
        )
    )

    assert payload["exported_at"] == "2026-05-11T05:32:00Z"
    assert payload["source_files"] == ["results.jsonl", "run_metadata.json"]
    assert payload["run"] == {
        "metadata": {"run_id": "empty-run"},
        "run_id": "empty-run",
    }
    assert payload["case_count"] == 0
    assert payload["agent_count"] == 0
    assert payload["variant_count"] == 0
    assert payload["task_count"] == 0
    assert payload["cases"] == []
    assert payload["agent_summaries"] == []


def test_export_run_json_handles_multi_task_variant_agent_matrix(tmp_path: Path) -> None:
    run_dir = tmp_path / "matrix-run"
    _write_run(
        run_dir,
        [
            CaseResult(
                run_id="run-1",
                case_id="task-b__experiment__agent-b__trial-2",
                task_id="task-b",
                variant="experiment",
                trial_index=2,
                repo_ref="main",
                agent_name="agent-b",
                network="disabled",
                status="completed",
                validation_status="passed",
                confidence="high",
                duration_seconds=7.0,
                telemetry_status="collected",
                telemetry_source="json-file",
                total_tokens=200,
                tool_call_count=5,
                tool_calls_by_name={"edit": 5},
            ),
            CaseResult(
                run_id="run-1",
                case_id="task-a__baseline__agent-a__trial-1",
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
                telemetry_status="collected",
                telemetry_source="json-file",
                total_tokens=100,
                tool_call_count=2,
                tool_calls_by_name={"read": 1, "edit": 1},
            ),
            CaseResult(
                run_id="run-1",
                case_id="task-a__experiment__agent-a__trial-1",
                task_id="task-a",
                variant="experiment",
                trial_index=1,
                repo_ref="main",
                agent_name="agent-a",
                network="disabled",
                status="validation_failed",
                validation_status="failed",
                confidence="low",
                duration_seconds=4.0,
            ),
        ],
    )

    payload = json.loads(
        export_run_json(
            run_dir,
            exported_at=datetime(2026, 5, 11, 5, 33, tzinfo=UTC),
        )
    )

    assert payload["case_count"] == 3
    assert payload["agent_count"] == 2
    assert payload["variant_count"] == 2
    assert payload["task_count"] == 2
    assert [
        (
            case["agent_name"],
            case["task_id"],
            case["variant"],
            case["trial_index"],
            case["case_id"],
        )
        for case in payload["cases"]
    ] == [
        ("agent-a", "task-a", "baseline", 1, "task-a__baseline__agent-a__trial-1"),
        ("agent-a", "task-a", "experiment", 1, "task-a__experiment__agent-a__trial-1"),
        ("agent-b", "task-b", "experiment", 2, "task-b__experiment__agent-b__trial-2"),
    ]
    assert payload["cases"][1]["total_tokens"] is None
    assert payload["cases"][1]["tool_call_count"] is None
    assert payload["cases"][1]["tool_calls_by_name"] == {}
