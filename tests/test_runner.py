import io
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

from context_eval import __version__
from context_eval.models import (
    RESULT_SCHEMA_VERSION,
    AgentConfig,
    AgentTelemetryConfig,
    ContextEvalConfig,
    EvaluationConfig,
    OverlayConfig,
    RepoConfig,
    TaskConfig,
    TaskFile,
    ValidationConfig,
    VariantConfig,
)
from context_eval.runner import ContextEvalRunner


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _create_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _run_git(repo, "add", "README.md")
    _run_git(
        repo,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test",
        "commit",
        "-m",
        "init",
    )
    return repo


def _quiet_console() -> Console:
    return Console(file=io.StringIO(), force_terminal=False)


def _base_config(
    *,
    tmp_path: Path,
    repo: Path,
    agent_command: str,
    overlay_source: Path,
    validation_commands: list[str] | None = None,
) -> ContextEvalConfig:
    return ContextEvalConfig(
        repo=RepoConfig(path=repo, base_ref="HEAD"),
        agent=AgentConfig(name="test-agent", command=agent_command, timeout_minutes=1),
        variants={
            "baseline": VariantConfig(
                description="Baseline",
                overlays=[OverlayConfig(source=overlay_source, target="AGENTS.md")],
            )
        },
        output_dir=tmp_path / "runs",
        evaluation=EvaluationConfig(commands=validation_commands or []),
    )


def test_runner_creates_versioned_result_report_and_agent_patch(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "from pathlib import Path\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'agent line\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    validation_script = tmp_path / "validate.py"
    validation_script.write_text(
        "from pathlib import Path\n"
        "readme = Path('README.md').read_text(encoding='utf-8')\n"
        "raise SystemExit(0 if 'agent line' in readme else 1)\n",
        encoding="utf-8",
    )

    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="smoke",
                prompt="Append a line.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{validation_script}"']),
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["schema_version"] == RESULT_SCHEMA_VERSION
    assert result["context_eval_version"] == __version__
    assert len(result["config_hash"]) == 16
    assert len(result["task_hash"]) == 16
    assert len(result["variant_hash"]) == 16
    assert result["status"] == "completed"
    assert result["validation_status"] == "passed"
    assert result["confidence"] == "high"
    assert result["telemetry_status"] == "unavailable"
    assert result["telemetry_source"] == "none"
    assert result["telemetry_error"] is None
    assert result["agent_duration_seconds"] >= 0
    assert result["prompt_tokens"] is None
    assert result["completion_tokens"] is None
    assert result["total_tokens"] is None
    assert result["reasoning_tokens"] is None
    assert result["tool_call_count"] is None
    assert result["tool_calls_by_name"] == {}
    assert result["changed_files"] == 1
    assert result["touched_paths"] == ["README.md"]
    assert result["workspace_retained"] is False
    assert result["cleanup_status"] == "succeeded"
    assert not (run_dir / result["workspace_path"]).exists()

    patch = (run_dir / result["patch_path"]).read_text(encoding="utf-8")
    assert "AGENTS.md" not in patch
    assert "+agent line" in patch

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "context-eval evaluates the effect of context variants" in report
    assert result["config_hash"] in report


def test_runner_records_json_file_agent_telemetry(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        "telemetry = Path(sys.argv[1])\n"
        "telemetry.parent.mkdir(parents=True, exist_ok=True)\n"
        "telemetry.write_text(json.dumps({\n"
        "    'prompt_tokens': 11,\n"
        "    'completion_tokens': 13,\n"
        "    'total_tokens': 24,\n"
        "    'reasoning_tokens': 3,\n"
        "    'tool_calls_by_name': {'read': 1, 'edit': 2},\n"
        "}), encoding='utf-8')\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'telemetry run\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    task_file = TaskFile(tasks=[TaskConfig(id="telemetry", prompt="Append a line.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}" "{{telemetry_file}}"',
        overlay_source=overlay_source,
    )
    config.agent.telemetry = AgentTelemetryConfig(collector="json-file")

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert result["telemetry_status"] == "collected"
    assert result["telemetry_source"] == "json-file"
    assert result["telemetry_error"] is None
    assert result["prompt_tokens"] == 11
    assert result["completion_tokens"] == 13
    assert result["total_tokens"] == 24
    assert result["reasoning_tokens"] == 3
    assert result["tool_call_count"] == 3
    assert result["tool_calls_by_name"] == {"read": 1, "edit": 2}


def test_runner_does_not_fail_case_when_json_telemetry_file_is_missing(
    tmp_path: Path,
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "from pathlib import Path\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'no telemetry\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    task_file = TaskFile(tasks=[TaskConfig(id="missing-telemetry", prompt="Append a line.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )
    config.agent.telemetry = AgentTelemetryConfig(collector="json-file")

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert result["telemetry_status"] == "unavailable"
    assert result["telemetry_source"] == "json-file"
    assert "telemetry file not found" in result["telemetry_error"]
    assert not any("telemetry collection failed" in error for error in result["errors"])


def test_runner_marks_validation_failure(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    validation_script = tmp_path / "validate.py"
    validation_script.write_text("raise SystemExit(1)\n", encoding="utf-8")

    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="failing-validation",
                prompt="Do nothing.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{validation_script}"']),
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "validation_failed"
    assert result["validation_status"] == "failed"
    assert result["confidence"] == "medium"
    assert result["validation_results"][0]["exit_code"] == 1


def test_runner_records_overlay_failure(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    agent_script = tmp_path / "agent.py"
    agent_script.write_text("raise SystemExit(0)\n", encoding="utf-8")
    missing_overlay = tmp_path / "missing" / "AGENTS.md"
    task_file = TaskFile(tasks=[TaskConfig(id="overlay-fail", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=missing_overlay,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "overlay_failed"
    assert result["validation_status"] == "skipped"
    assert result["confidence"] == "low"
    assert result["errors"]


def test_runner_guards_unique_run_directories_for_same_second(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    task_file = TaskFile(tasks=[TaskConfig(id="same-second", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    class FrozenDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 1, 2, 3, 4, 5)

    monkeypatch.setattr("context_eval.runner.datetime", FrozenDateTime)

    first_run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        console=_quiet_console(),
    ).run()
    second_run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        console=_quiet_console(),
    ).run()

    assert first_run_dir != second_run_dir
    assert first_run_dir.name == "20260102-030405"
    assert second_run_dir.name == "20260102-030405-2"

    for run_dir in [first_run_dir, second_run_dir]:
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
        result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))
        assert metadata["run_id"] == run_dir.name
        assert result["run_id"] == run_dir.name


def test_runner_records_cleanup_skipped_when_workspace_is_retained(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    task_file = TaskFile(tasks=[TaskConfig(id="retain-workspace", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=False,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["workspace_retained"] is True
    assert result["cleanup_status"] == "skipped"
    assert (run_dir / result["workspace_path"]).exists()


def test_runner_records_cleanup_failure_without_hiding_result(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    task_file = TaskFile(tasks=[TaskConfig(id="cleanup-fails", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    def fail_cleanup(repo_path: Path, workspace: Path) -> None:
        raise RuntimeError("cannot remove workspace")

    monkeypatch.setattr("context_eval.runner.remove_workspace", fail_cleanup)

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert result["workspace_retained"] is True
    assert result["cleanup_status"] == "failed"
    assert (run_dir / result["workspace_path"]).exists()
    assert any("workspace cleanup failed" in error for error in result["errors"])


def test_runner_records_workspace_failure_without_running_case_steps(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    sentinel_path = tmp_path / "agent-ran.txt"
    agent_script.write_text(
        f"from pathlib import Path\nPath({str(sentinel_path)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="missing-ref",
                prompt="Do nothing.",
                repo_ref="refs/heads/does-not-exist",
                validation=ValidationConfig(commands=["python -c \"raise SystemExit(42)\""]),
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "workspace_failed"
    assert result["workspace_path"] is None
    assert result["prompt_path"] is None
    assert result["stdout_path"] is None
    assert result["stderr_path"] is None
    assert result["validation_results"] == []
    assert result["validation_status"] == "skipped"
    assert result["cleanup_status"] == "skipped"
    assert result["workspace_retained"] is False
    assert result["errors"]
    assert not sentinel_path.exists()


def test_runner_repeats_selected_cases_for_trials(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('trial run')\n", encoding="utf-8")
    task_file = TaskFile(tasks=[TaskConfig(id="repeat", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        trials=2,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert len(results) == 2
    assert [result["trial_index"] for result in results] == [1, 2]
    assert [result["case_id"] for result in results] == [
        "repeat__baseline__trial-1",
        "repeat__baseline__trial-2",
    ]
    assert len({result["prompt_path"] for result in results}) == 2
    assert len({result["stdout_path"] for result in results}) == 2
    assert len({result["patch_path"] for result in results}) == 2
    assert len({result["workspace_path"] for result in results}) == 2
