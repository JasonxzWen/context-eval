from pathlib import Path

from typer.testing import CliRunner

from context_eval.cli import app


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
