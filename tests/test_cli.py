from pathlib import Path

from typer.testing import CliRunner

from context_eval.cli import app
from context_eval.config import validate_config_files
from context_eval.models import CaseResult


def _write_results_jsonl(run_dir: Path, results: list[CaseResult]) -> None:
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )


def _large_local_matrix_results() -> list[CaseResult]:
    return [
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
            agent_duration_seconds=1.25,
            telemetry_status="collected",
            telemetry_source="json-file",
            total_tokens=100,
            tool_call_count=2,
            tool_calls_by_name={"read": 1, "edit": 1},
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-a__baseline__agent-a__trial-2",
            task_id="task-a",
            variant="baseline",
            trial_index=2,
            repo_ref="main",
            agent_name="agent-a",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
            duration_seconds=3.0,
            telemetry_status="partial",
            telemetry_source="json-file",
            telemetry_error="completion_tokens must be a non-negative integer",
            total_tokens=120,
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-a__baseline__agent-b__trial-1",
            task_id="task-a",
            variant="baseline",
            trial_index=1,
            repo_ref="main",
            agent_name="agent-b",
            network="disabled",
            status="timeout",
            timeout=True,
            validation_status="failed",
            confidence="medium",
            duration_seconds=6.0,
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
            errors=["pytest failed"],
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-b__baseline__agent-b__trial-1",
            task_id="task-b",
            variant="baseline",
            trial_index=1,
            repo_ref="main",
            agent_name="agent-b",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
            duration_seconds=5.0,
            telemetry_status="collected",
            telemetry_source="json-file",
            tool_call_count=1,
            tool_calls_by_name={"test": 1},
        ),
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
            agent_duration_seconds=6.5,
            total_tokens=200,
            tool_call_count=5,
            tool_calls_by_name={"edit": 5},
        ),
    ]


def test_validate_config_exposes_strict_option(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix the bug."
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
  base_ref: "HEAD"
agent:
  name: "test-agent"
  command: "agent -p {prompt_file}"
tasks: "./tasks.yaml"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["validate-config", "--config", str(config_path), "--strict"],
    )

    assert result.exit_code == 1
    assert "repo.path is not a Git repository" in result.output


def test_validate_config_check_agents_reports_missing_profile_executable(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix the bug."
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
agents:
  trae:
    kind: "traecli"
    command: "missing-traecli -p \\"{prompt}\\""
tasks: "./tasks.yaml"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["validate-config", "--config", str(config_path), "--check-agents"],
    )

    assert result.exit_code == 1
    assert "agents.trae.command executable not found" in result.output
    assert "missing-traecli" in result.output


def test_validate_config_prints_field_specific_schema_error(tmp_path: Path) -> None:
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix the bug."
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  base_ref: "HEAD"
agent:
  name: "test-agent"
  command: "agent -p {prompt_file}"
tasks: "./tasks.yaml"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["validate-config", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "Invalid config:" in result.output
    assert "context-eval.yaml: repo.path" in result.output


def test_run_exposes_task_filters_and_fails_unknown_task_id(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "known"
    prompt: "Fix the bug."
    category: "documentation"
    difficulty: "easy"
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
  base_ref: "HEAD"
agent:
  name: "test-agent"
  command: "agent -p {prompt_file}"
tasks: "./tasks.yaml"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--config",
            str(config_path),
            "--task-id",
            "missing",
            "--category",
            "documentation",
            "--difficulty",
            "easy",
        ],
    )

    assert result.exit_code == 1
    assert "unknown task id" in result.output


def test_run_dry_run_prints_matrix_and_creates_no_artifacts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts"
    (context_dir / "baseline").mkdir(parents=True)
    (context_dir / "experiment").mkdir(parents=True)
    (context_dir / "baseline" / "AGENTS.md").write_text("# Baseline\n", encoding="utf-8")
    (context_dir / "experiment" / "AGENTS.md").write_text("# Experiment\n", encoding="utf-8")
    tasks_path = tmp_path / "tasks.yaml"
    tasks_path.write_text(
        """
tasks:
  - id: "docs-easy"
    prompt: "Fix docs."
    category: "documentation"
    difficulty: "easy"
  - id: "runtime-hard"
    prompt: "Fix runtime."
    category: "runtime"
    difficulty: "hard"
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    output_dir = tmp_path / "runs"
    config_path.write_text(
        f"""
repo:
  path: "./repo"
  base_ref: "main"
agent:
  name: "test-agent"
  command: "agent -p {{prompt_file}}"
tasks: "./tasks.yaml"
output_dir: "{output_dir.as_posix()}"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
  experiment:
    description: "Experiment"
    overlays:
      - source: "./contexts/experiment/AGENTS.md"
        target: "AGENTS.md"
evaluation:
  timeout_seconds: 30
  commands:
    - "python -m pytest"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--config",
            str(config_path),
            "--dry-run",
            "--category",
            "documentation",
            "--variant",
            "experiment",
        ],
    )

    assert result.exit_code == 0
    assert "Dry run" in result.output
    assert "docs-easy" in result.output
    assert "runtime-hard" not in result.output
    assert "experiment" in result.output
    assert "baseline" not in result.output
    assert "repo_ref=main" in result.output
    assert "AGENTS.md -> AGENTS.md" in result.output
    assert "prompts/docs-easy__experiment.md" in result.output
    assert "python -m pytest" in result.output
    assert "timeout_seconds=30" in result.output
    assert not output_dir.exists()

    max_tasks_result = CliRunner().invoke(
        app,
        ["run", "--config", str(config_path), "--dry-run", "--max-tasks", "1"],
    )

    assert max_tasks_result.exit_code == 0
    assert "docs-easy" in max_tasks_result.output
    assert "runtime-hard" not in max_tasks_result.output
    assert not output_dir.exists()

    trials_result = CliRunner().invoke(
        app,
        [
            "run",
            "--config",
            str(config_path),
            "--dry-run",
            "--trials",
            "2",
            "--jobs",
            "2",
            "--cleanup-policy",
            "failed",
            "--variant",
            "baseline",
            "--max-tasks",
            "1",
        ],
    )

    assert trials_result.exit_code == 0
    assert "Jobs: 2" in trials_result.output
    assert "Cleanup policy: failed" in trials_result.output
    assert "trial=2" in trials_result.output
    assert "docs-easy__baseline__trial-2" in trials_result.output
    assert not output_dir.exists()


def test_run_dry_run_expands_agents_map_and_filters_agent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Baseline\n", encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "docs-easy"
    prompt: "Fix docs."
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    output_dir = tmp_path / "runs"
    config_path.write_text(
        f"""
repo:
  path: "./repo"
  base_ref: "main"
agents:
  codex:
    kind: "codex-cli"
    command: "codex exec - < {{prompt_file}}"
  coco:
    kind: "custom"
    command: "coco -p {{prompt_file}}"
  trae:
    kind: "traecli"
    command: "traecli -p \\"{{prompt}}\\""
tasks: "./tasks.yaml"
output_dir: "{output_dir.as_posix()}"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--config",
            str(config_path),
            "--dry-run",
            "--agent",
            "trae",
            "--trials",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert "Agents: trae" in result.output
    assert 'trae (traecli): traecli -p "{prompt}"' in result.output
    assert "agent=trae task=docs-easy variant=baseline trial=2" in result.output
    assert "docs-easy__baseline__trae__trial-2" in result.output
    assert "agent=codex" not in result.output
    assert "codex (codex-cli)" not in result.output
    assert "agent=coco" not in result.output
    assert not output_dir.exists()


def test_init_generates_valid_starter_files(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "init",
            "--directory",
            str(tmp_path),
            "--repo-path",
            ".",
            "--agent-command",
            "agent -p {prompt_file}",
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "context-eval.yaml").exists()
    assert (tmp_path / "tasks.yaml").exists()
    assert (tmp_path / "contexts" / "baseline" / "AGENTS.md").exists()
    assert (tmp_path / "contexts" / "experiment" / "AGENTS.md").exists()

    config, task_file = validate_config_files(tmp_path / "context-eval.yaml")
    assert config.repo.path == tmp_path.resolve()
    assert config.agent.command == "agent -p {prompt_file}"
    assert task_file.tasks[0].id == "sample-task"


def test_init_can_generate_named_agent_profiles(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "init",
            "--directory",
            str(tmp_path),
            "--repo-path",
            ".",
            "--agent-command",
            "coco -p {prompt_file}",
            "--agent-profiles",
        ],
    )

    assert result.exit_code == 0
    config_text = (tmp_path / "context-eval.yaml").read_text(encoding="utf-8")
    assert "\nagents:\n" in f"\n{config_text}"
    assert "\nagent:\n" not in f"\n{config_text}"

    config, task_file = validate_config_files(tmp_path / "context-eval.yaml")
    assert config.agent is None
    assert list(config.agents) == ["codex", "claude", "trae", "custom"]
    assert config.agents["codex"].kind == "codex-cli"
    assert config.agents["claude"].kind == "claude-code"
    assert config.agents["trae"].command == 'traecli -p "{prompt}"'
    assert config.agents["custom"].command == "coco -p {prompt_file}"
    assert task_file.tasks[0].id == "sample-task"


def test_init_refuses_to_overwrite_existing_files_without_force(tmp_path: Path) -> None:
    (tmp_path / "tasks.yaml").write_text("existing\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["init", "--directory", str(tmp_path)])

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert (tmp_path / "tasks.yaml").read_text(encoding="utf-8") == "existing\n"


def test_init_force_overwrites_existing_files(tmp_path: Path) -> None:
    (tmp_path / "tasks.yaml").write_text("existing\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["init", "--directory", str(tmp_path), "--force"])

    assert result.exit_code == 0
    assert "sample-task" in (tmp_path / "tasks.yaml").read_text(encoding="utf-8")


def test_inspect_run_prints_results_from_jsonl(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        '{"run_id": "run-1", "agent": {"name": "agent"}, "repo": {"base_ref": "main"}}',
        encoding="utf-8",
    )
    result = CaseResult(
        run_id="run-1",
        case_id="task-1__baseline",
        trial_index=1,
        task_id="task-1",
        variant="baseline",
        repo_ref="main",
        agent_name="agent",
        network="disabled",
        status="completed",
        validation_status="passed",
        confidence="high",
        changed_files=2,
        telemetry_status="collected",
        telemetry_source="json-file",
        agent_duration_seconds=1.25,
        total_tokens=24,
        tool_call_count=3,
    )
    (run_dir / "results.jsonl").write_text(result.model_dump_json() + "\n", encoding="utf-8")

    output = CliRunner().invoke(app, ["inspect-run", str(run_dir)])

    assert output.exit_code == 0
    assert "run-1" in output.output
    assert "Results: 1" in output.output
    assert "task-1" in output.output
    assert "baseline" in output.output
    assert "completed" in output.output
    assert "passed" in output.output
    assert "high" in output.output
    assert "2" in output.output
    assert "telemetry_status=collected" in output.output
    assert "agent_duration=1.25" in output.output
    assert "total_tokens=24" in output.output
    assert "tool_calls=3" in output.output


def test_inspect_run_prints_unavailable_telemetry_from_jsonl(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = CaseResult(
        run_id="run-1",
        case_id="task-1__baseline",
        task_id="task-1",
        variant="baseline",
        repo_ref="main",
        agent_name="agent",
        network="disabled",
        status="completed",
        validation_status="passed",
        confidence="high",
    )
    (run_dir / "results.jsonl").write_text(result.model_dump_json() + "\n", encoding="utf-8")

    output = CliRunner().invoke(app, ["inspect-run", str(run_dir)])

    assert output.exit_code == 0
    assert "telemetry_status=unavailable" in output.output
    assert "agent_duration=-" in output.output
    assert "total_tokens=-" in output.output
    assert "tool_calls=-" in output.output


def test_inspect_run_fails_for_missing_results(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    output = CliRunner().invoke(app, ["inspect-run", str(run_dir)])

    assert output.exit_code == 1
    assert "results file not found" in output.output


def test_compare_prints_variant_metrics_from_jsonl(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        '{"run_id": "run-1", "agent": {"name": "agent"}, "repo": {"base_ref": "main"}}',
        encoding="utf-8",
    )
    results = [
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
            duration_seconds=2.0,
            agent_duration_seconds=1.5,
            telemetry_status="collected",
            telemetry_source="json-file",
            total_tokens=100,
            tool_call_count=4,
            tool_calls_by_name={"read": 1, "edit": 3},
            changed_files=1,
            touched_paths=["a.py"],
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-2__baseline",
            task_id="task-2",
            variant="baseline",
            repo_ref="main",
            agent_name="agent",
            network="disabled",
            status="timeout",
            timeout=True,
            validation_status="failed",
            confidence="medium",
            duration_seconds=4.0,
            changed_files=3,
            touched_paths=["a.py", "b.py"],
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-1__experiment",
            task_id="task-1",
            variant="experiment",
            repo_ref="main",
            agent_name="agent",
            network="disabled",
            status="agent_failed",
            validation_status="skipped",
            confidence="low",
            duration_seconds=1.0,
            changed_files=0,
            touched_paths=[],
        ),
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )

    output = CliRunner().invoke(app, ["compare", str(run_dir)])

    assert output.exit_code == 0
    assert "run-1" in output.output
    assert "baseline" in output.output
    assert "experiment" in output.output
    assert "pass_rate=50.0%" in output.output
    assert "timeout_rate=50.0%" in output.output
    assert "agent_failure_rate=100.0%" in output.output
    assert "validation_failure_rate=50.0%" in output.output
    assert "avg_duration=3.00" in output.output
    assert "avg_changed_files=2.00" in output.output
    assert "common_touched_paths=a.py" in output.output
    assert "telemetry_statuses=collected=1,unavailable=1" in output.output
    assert "avg_agent_duration=1.50" in output.output
    assert "avg_total_tokens=100.00" in output.output
    assert "avg_tool_calls=4.00" in output.output
    assert "common_tool_names=edit,read" in output.output
    assert "telemetry_statuses=unavailable=1" in output.output
    assert "avg_total_tokens=-" in output.output


def test_inspect_run_prints_agent_summary_for_multiple_agents(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        """
{
  "run_id": "run-1",
  "agent": {"name": "agent-a"},
  "agents": [{"name": "agent-a"}, {"name": "agent-b"}],
  "repo": {"base_ref": "main"}
}
""",
        encoding="utf-8",
    )
    results = [
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline__agent-a",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent-a",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
            duration_seconds=2.0,
            agent_duration_seconds=1.5,
            total_tokens=50,
            tool_call_count=2,
            telemetry_status="collected",
            telemetry_source="json-file",
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline__agent-b",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent-b",
            network="disabled",
            status="agent_failed",
            validation_status="skipped",
            confidence="low",
            duration_seconds=4.0,
        ),
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )

    output = CliRunner().invoke(app, ["inspect-run", str(run_dir)])

    assert output.exit_code == 0
    assert "Agent profiles: agent-a, agent-b" in output.output
    assert "Agents:" in output.output
    assert "agent=agent-a cases=1 pass_rate=100.0%" in output.output
    assert "avg_agent_duration=1.50" in output.output
    assert "avg_total_tokens=50.00" in output.output
    assert "telemetry_statuses=collected=1" in output.output
    assert "agent=agent-b cases=1 pass_rate=0.0%" in output.output
    assert "avg_agent_duration=-" in output.output
    assert "telemetry_statuses=unavailable=1" in output.output


def test_inspect_run_suppresses_agent_summary_for_single_agent(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = CaseResult(
        run_id="run-1",
        case_id="task-1__baseline",
        task_id="task-1",
        variant="baseline",
        repo_ref="main",
        agent_name="agent-a",
        network="disabled",
        status="completed",
        validation_status="passed",
        confidence="high",
    )
    (run_dir / "results.jsonl").write_text(result.model_dump_json() + "\n", encoding="utf-8")

    output = CliRunner().invoke(app, ["inspect-run", str(run_dir)])

    assert output.exit_code == 0
    assert "Agents:" not in output.output


def test_compare_prints_agent_summary_for_multiple_agents(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    results = [
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline__agent-a",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent-a",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
            duration_seconds=2.0,
            agent_duration_seconds=1.5,
            total_tokens=50,
            tool_call_count=2,
            telemetry_status="collected",
            telemetry_source="json-file",
            tool_calls_by_name={"read": 2},
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline__agent-b",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent-b",
            network="disabled",
            status="timeout",
            timeout=True,
            validation_status="failed",
            confidence="medium",
            duration_seconds=4.0,
        ),
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )

    output = CliRunner().invoke(app, ["compare", str(run_dir)])

    assert output.exit_code == 0
    assert "Agents:" in output.output
    assert "agent=agent-a cases=1 pass_rate=100.0%" in output.output
    assert "avg_duration=2.00" in output.output
    assert "avg_agent_duration=1.50" in output.output
    assert "avg_tool_calls=2.00" in output.output
    assert "common_tool_names=read" in output.output
    assert "agent=agent-b cases=1 pass_rate=0.0%" in output.output


def test_compare_prints_large_matrix_overview_from_local_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_results_jsonl(run_dir, _large_local_matrix_results())

    output = CliRunner().invoke(app, ["compare", str(run_dir)])

    assert output.exit_code == 0
    assert (
        "Local observations only; sourced from results.jsonl and optional run_metadata.json"
        in output.output
    )
    assert (
        "Matrix: tasks=2 variants=2 agents=2 trials=2 cases=6 failed=2 "
        "timeouts=1 low_confidence=1 telemetry_gaps=3"
    ) in output.output
    assert (
        "cell task=task-a variant=baseline cases=3 pass_rate=66.7% "
        "statuses=completed=2,timeout=1 validation=passed=2,failed=1 "
        "confidence=high=2,medium=1 agents=agent-a,agent-b trials=1,2"
    ) in output.output


def test_report_writes_telemetry_summary_from_jsonl(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        '{"run_id": "run-1", "agent": {"name": "agent"}, "repo": {"base_ref": "main"}}',
        encoding="utf-8",
    )
    results = [
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
            agent_duration_seconds=2.0,
            telemetry_status="collected",
            telemetry_source="json-file",
            total_tokens=80,
            tool_call_count=2,
            tool_calls_by_name={"read": 2},
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-1__experiment",
            task_id="task-1",
            variant="experiment",
            repo_ref="main",
            agent_name="agent",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
        ),
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )

    output = CliRunner().invoke(app, ["report", str(run_dir)])

    assert output.exit_code == 0
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "context-eval evaluates the effect of context variants" in report
    assert "## Telemetry Summary" in report
    assert "| `baseline` | collected=1 | 2.00 | 80.00 | 2.00 | read |" in report
    assert "| `experiment` | unavailable=1 | - | - | - | - |" in report
    assert "## Agent Summary" not in report


def test_report_writes_agent_summary_for_multiple_agents(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        '{"run_id": "run-1", "agent": {"name": "mixed"}, "repo": {"base_ref": "main"}}',
        encoding="utf-8",
    )
    results = [
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline__agent-a",
            task_id="task-1",
            variant="baseline",
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
            total_tokens=80,
            tool_call_count=2,
            tool_calls_by_name={"read": 2},
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-2__baseline__agent-a",
            task_id="task-2",
            variant="baseline",
            repo_ref="main",
            agent_name="agent-a",
            network="disabled",
            status="validation_failed",
            validation_status="failed",
            confidence="medium",
            duration_seconds=4.0,
            telemetry_status="partial",
            telemetry_source="json-file",
            total_tokens=40,
            tool_call_count=4,
            tool_calls_by_name={"edit": 4},
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline__agent-b",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent-b",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
            duration_seconds=8.0,
        ),
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )

    output = CliRunner().invoke(app, ["report", str(run_dir)])

    assert output.exit_code == 0
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "context-eval evaluates the effect of context variants" in report
    assert "not the absolute capability of an agent" in report
    assert "## Agent Summary" in report
    assert (
        "| `agent-a` | 2 | 50.0% | 3.00 | 1.50 | 60.00 | 3.00 | "
        "collected=1,partial=1 | edit,read |"
    ) in report
    assert "| `agent-b` | 1 | 100.0% | 8.00 | - | - | - | unavailable=1 | - |" in report


def test_report_polishes_large_multi_axis_local_matrix(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text(
        '{"run_id": "run-1", "agent": {"name": "mixed"}, "repo": {"base_ref": "main"}}',
        encoding="utf-8",
    )
    _write_results_jsonl(run_dir, _large_local_matrix_results())

    output = CliRunner().invoke(app, ["report", str(run_dir)])

    assert output.exit_code == 0
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "## Run Matrix Overview" in report
    assert "| Task count | 2 |" in report
    assert "| Variant count | 2 |" in report
    assert "| Agent count | 2 |" in report
    assert "| Trial count | 2 |" in report
    assert "| Case count | 6 |" in report
    assert "| Failed cases | 2 |" in report
    assert "| Timeout cases | 1 |" in report
    assert "| Low-confidence cases | 1 |" in report
    assert "| Telemetry-gap cases | 3 |" in report
    assert (
        "cases=3; pass_rate=66.7%; statuses=completed=2,timeout=1; "
        "validation=passed=2,failed=1; confidence=high=2,medium=1; "
        "agents=agent-a,agent-b; trials=1,2"
    ) in report
    assert "## Risk Signals" in report
    assert "### Failed And Timeout Cases" in report
    assert (
        "| `task-a` | `experiment` | `agent-a` | 1 | `validation_failed` | "
        "`failed` | `low` | pytest failed |"
    ) in report
    assert "### Low Confidence Cases" in report
    assert "| `task-a` | `experiment` | `agent-a` | 1 | `validation_failed` | `failed` |" in report
    assert "### Telemetry Gap Cases" in report
    assert (
        "| `task-a` | `baseline` | `agent-a` | 2 | `partial` | `json-file` | "
        "completion_tokens must be a non-negative integer |"
    ) in report
    assert "| `task-a` | `baseline` | `agent-b` | 1 | `unavailable` | `none` | - |" in report


def test_compare_fails_for_missing_results(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    output = CliRunner().invoke(app, ["compare", str(run_dir)])

    assert output.exit_code == 1
    assert "results file not found" in output.output


def test_compare_fails_for_malformed_results(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "results.jsonl").write_text("{not-json}\n", encoding="utf-8")

    output = CliRunner().invoke(app, ["compare", str(run_dir)])

    assert output.exit_code == 1
    assert "malformed results.jsonl line 1" in output.output


def test_export_writes_csv_from_run_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = CaseResult(
        run_id="run-1",
        case_id="task-1__baseline",
        task_id="task-1",
        variant="baseline",
        repo_ref="main",
        agent_name="agent-a",
        network="disabled",
        status="completed",
        validation_status="passed",
        confidence="high",
        total_tokens=10,
    )
    (run_dir / "results.jsonl").write_text(result.model_dump_json() + "\n", encoding="utf-8")
    output_path = tmp_path / "summary.csv"

    output = CliRunner().invoke(
        app,
        ["export", str(run_dir), "--format", "csv", "--output", str(output_path)],
    )

    assert output.exit_code == 0
    assert "Export written" in output.output
    csv_text = output_path.read_text(encoding="utf-8")
    assert "run_id,case_id,agent_name,task_id" in csv_text
    assert "run-1,task-1__baseline,agent-a,task-1" in csv_text


def test_export_writes_compact_json_from_run_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text('{"run_id": "run-1"}', encoding="utf-8")
    result = CaseResult(
        run_id="run-1",
        case_id="task-1__baseline",
        task_id="task-1",
        variant="baseline",
        repo_ref="main",
        agent_name="agent-a",
        network="disabled",
        status="completed",
        validation_status="passed",
        confidence="high",
        total_tokens=10,
    )
    (run_dir / "results.jsonl").write_text(result.model_dump_json() + "\n", encoding="utf-8")
    output_path = tmp_path / "summary.json"

    output = CliRunner().invoke(
        app,
        ["export", str(run_dir), "--format", "json", "--output", str(output_path)],
    )

    assert output.exit_code == 0
    json_text = output_path.read_text(encoding="utf-8")
    assert '"agent_summaries"' in json_text
    assert '"agent_name": "agent-a"' in json_text
    assert '"total_tokens": 10' in json_text


def test_export_rejects_unsupported_format(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "results.jsonl").write_text("", encoding="utf-8")

    output = CliRunner().invoke(
        app,
        ["export", str(run_dir), "--format", "xml", "--output", str(tmp_path / "out.xml")],
    )

    assert output.exit_code == 1
    assert "unsupported export format" in output.output


def test_ui_generates_self_contained_config_and_run_html(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts"
    (context_dir / "baseline").mkdir(parents=True)
    (context_dir / "experiment").mkdir(parents=True)
    (context_dir / "baseline" / "AGENTS.md").write_text("# Baseline\n", encoding="utf-8")
    (context_dir / "experiment" / "AGENTS.md").write_text("# Experiment\n", encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix docs."
    category: "documentation"
    difficulty: "easy"
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
  base_ref: "main"
agent:
  name: "test-agent"
  command: "agent -p {prompt_file}"
tasks: "./tasks.yaml"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
  experiment:
    description: "Experiment"
    overlays:
      - source: "./contexts/experiment/AGENTS.md"
        target: "AGENTS.md"
evaluation:
  commands:
    - "python -m pytest"
""",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_metadata.json").write_text('{"run_id": "run-1"}', encoding="utf-8")
    result = CaseResult(
        run_id="run-1",
        case_id="task-1__baseline",
        task_id="task-1",
        variant="baseline",
        repo_ref="main",
        agent_name="agent",
        network="disabled",
        status="completed",
        validation_status="passed",
        confidence="high",
        changed_files=1,
        touched_paths=["a.py"],
    )
    (run_dir / "results.jsonl").write_text(result.model_dump_json() + "\n", encoding="utf-8")
    output_path = tmp_path / "context-eval-ui.html"

    output = CliRunner().invoke(
        app,
        [
            "ui",
            "--config",
            str(config_path),
            "--run-dir",
            str(run_dir),
            "--output",
            str(output_path),
        ],
    )

    assert output.exit_code == 0
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "context-eval local UI" in html
    assert str(repo.resolve()) in html
    assert "agent -p {prompt_file}" in html
    assert "task-1" in html
    assert "baseline" in html
    assert "experiment" in html
    assert "run-1" in html
    assert "completed" in html
    assert "pass_rate=100.0%" in html
    assert 'data-role="config-editor"' in html
    for field in [
        "repo.path",
        "repo.base_ref",
        "agent.name",
        "agent.kind",
        "agent.command",
        "agent.timeout_minutes",
        "agent.network",
        "tasks_path",
        "evaluation_commands",
        "evaluation_timeout_seconds",
        "variant.name",
        "variant.description",
        "overlay.source",
        "overlay.target",
        "task.id",
        "task.title",
        "task.prompt",
        "task.repo_ref",
        "task.category",
        "task.difficulty",
        "task.validation_commands",
        "task.validation_timeout_seconds",
    ]:
        assert f'data-field="{field}"' in html
    assert 'id="matrix-body"' in html
    assert 'data-role="validation-preflight"' in html
    assert 'id="preflight-status"' in html
    assert 'id="preflight-issues"' in html
    assert 'id="validate-config-command"' in html
    assert 'data-role="persistence-mode"' in html
    assert 'data-persistence-mode="static-export-only"' in html
    assert 'data-server-mode="disabled"' in html
    assert "Mode: static export-only" in html
    assert "Server endpoints: disabled" in html
    assert "Direct file writes: disabled" in html
    assert "Agent and validation execution: disabled" in html
    assert 'data-role="yaml-export"' in html
    assert 'id="config-yaml-export"' in html
    assert 'id="tasks-yaml-export"' in html
    assert 'data-copy-target="config-yaml-export"' in html
    assert 'data-download-target="config-yaml-export"' in html
    assert 'data-copy-target="tasks-yaml-export"' in html
    assert 'data-download-target="tasks-yaml-export"' in html
    assert "Static mode cannot save directly to disk" in html
    assert (
        "Static mode does not run agents, validation commands, workspaces, or network actions."
        in html
    )
    assert "context-eval validate-config --config" in html
    assert "No schema-level issues detected in edited YAML." in html
    assert "Schema preflight found" in html
    assert "repo.path" in html
    assert " is required" in html
    assert '" prompt"' in html
    assert "agent.network must be disabled or enabled" in html
    assert "agent.kind must be custom, codex-cli, claude-code, or traecli" in html
    assert "target must be a safe relative path" in html
    assert "function renderMatrix" in html
    assert "function validateEditedConfiguration" in html
    assert "function validateExportModel" in html
    assert "function validateGeneratedYaml" in html
    assert "function refreshValidationPreflight" in html
    assert "function renderConfigYaml" in html
    assert "function renderTasksYaml" in html
    assert "function downloadYaml" in html
    assert "function copyYaml" in html
    assert 'addEventListener("input"' in html
    assert "http://" not in html
    assert "https://" not in html
    assert "<script src=" not in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "WebSocket" not in html
    assert "EventSource" not in html
    assert "sendBeacon" not in html
    assert "localStorage" not in html
    assert "showSaveFilePicker" not in html
    assert "showOpenFilePicker" not in html
    assert "data-save-target" not in html


def test_ui_config_preview_preserves_agents_map_semantics(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Baseline\n", encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix docs."
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
  base_ref: "main"
agents:
  codex:
    kind: "codex-cli"
    command: "codex exec - < {prompt_file}"
  coco:
    kind: "custom"
    command: "coco -p {prompt_file}"
  trae:
    kind: "traecli"
    command: "traecli -p \\"{prompt}\\""
tasks: "./tasks.yaml"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
""",
        encoding="utf-8",
    )
    output_path = tmp_path / "context-eval-ui.html"

    output = CliRunner().invoke(
        app,
        ["ui", "--config", str(config_path), "--output", str(output_path)],
    )

    assert output.exit_code == 0
    html = output_path.read_text(encoding="utf-8")
    assert "Agent x Task x Variant Matrix" in html
    assert "task-1__baseline__codex" in html
    assert "task-1__baseline__coco" in html
    assert "task-1__baseline__trae" in html
    assert '"agent_shape": "agents"' in html
    assert '"kind": "codex-cli"' in html
    assert '"kind": "traecli"' in html
    assert 'editableModel.agent_shape === "agents" ? "agents:" : "agent:"' in html


def test_ui_shows_agent_summary_from_run_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    results = [
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline__agent-a",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent-a",
            network="disabled",
            status="completed",
            validation_status="passed",
            confidence="high",
            duration_seconds=2.0,
            agent_duration_seconds=1.5,
            total_tokens=40,
            tool_call_count=2,
            telemetry_status="collected",
            telemetry_source="json-file",
            tool_calls_by_name={"read": 2},
        ),
        CaseResult(
            run_id="run-1",
            case_id="task-1__baseline__agent-b",
            task_id="task-1",
            variant="baseline",
            repo_ref="main",
            agent_name="agent-b",
            network="disabled",
            status="timeout",
            timeout=True,
            validation_status="failed",
            confidence="medium",
            duration_seconds=6.0,
        ),
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(result.model_dump_json() for result in results) + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "context-eval-ui.html"

    output = CliRunner().invoke(
        app,
        ["ui", "--run-dir", str(run_dir), "--output", str(output_path)],
    )

    assert output.exit_code == 0
    html = output_path.read_text(encoding="utf-8")
    assert "Agent Metrics" in html
    assert "agent-a" in html
    assert "agent-b" in html
    assert "avg_agent_duration=1.50" in html
    assert "avg_total_tokens=40.00" in html
    assert "avg_tool_calls=2.00" in html
    assert "telemetry_statuses=collected=1" in html
    assert "telemetry_statuses=unavailable=1" in html
    assert "common_tool_names=read" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "WebSocket" not in html


def test_ui_shows_large_matrix_overview_and_telemetry_columns(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_results_jsonl(run_dir, _large_local_matrix_results())
    output_path = tmp_path / "context-eval-ui.html"

    output = CliRunner().invoke(
        app,
        ["ui", "--run-dir", str(run_dir), "--output", str(output_path)],
    )

    assert output.exit_code == 0
    html = output_path.read_text(encoding="utf-8")
    assert "Run Matrix Overview" in html
    assert "tasks=2" in html
    assert "variants=2" in html
    assert "agents=2" in html
    assert "trials=2" in html
    assert "cases=6" in html
    assert "failed=2" in html
    assert "telemetry_gaps=3" in html
    assert "Large Matrix Cells" in html
    assert "cases=3" in html
    assert "pass_rate=66.7%" in html
    assert "agents=agent-a,agent-b" in html
    assert "<th>Agent</th>" in html
    assert "<th>Telemetry</th>" in html
    assert "<th>Agent duration</th>" in html
    assert "<th>Total tokens</th>" in html
    assert "<th>Tool calls</th>" in html
    assert "<td><code>agent-a</code></td>" in html
    assert "<td><code>partial</code></td>" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "WebSocket" not in html


def test_ui_requires_config_or_run_dir(tmp_path: Path) -> None:
    output = CliRunner().invoke(app, ["ui", "--output", str(tmp_path / "ui.html")])

    assert output.exit_code == 1
    assert "requires --config or --run-dir" in output.output
