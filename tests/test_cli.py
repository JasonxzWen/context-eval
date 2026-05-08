from pathlib import Path

from typer.testing import CliRunner

from context_eval.cli import app
from context_eval.config import validate_config_files
from context_eval.models import CaseResult


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
            "--variant",
            "baseline",
            "--max-tasks",
            "1",
        ],
    )

    assert trials_result.exit_code == 0
    assert "trial=2" in trials_result.output
    assert "docs-easy__baseline__trial-2" in trials_result.output
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
    assert "http://" not in html
    assert "https://" not in html


def test_ui_requires_config_or_run_dir(tmp_path: Path) -> None:
    output = CliRunner().invoke(app, ["ui", "--output", str(tmp_path / "ui.html")])

    assert output.exit_code == 1
    assert "requires --config or --run-dir" in output.output
