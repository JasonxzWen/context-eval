from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml
from typer.main import get_command
from typer.testing import CliRunner

from context_eval.cli import app
from context_eval.local_app import LocalAppError, LocalAppService


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"command failed: {' '.join(command)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result


def _create_git_repo(path: Path) -> Path:
    path.mkdir()
    _run(["git", "init"], cwd=path)
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=path)
    _run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-m",
            "init",
        ],
        cwd=path,
    )
    _run(["git", "branch", "-M", "main"], cwd=path)
    return path


def _write_eval_files(
    workspace: Path,
    repo: Path,
    *,
    agent_command: str | None = None,
    validation_commands: list[str] | None = None,
) -> Path:
    context_dir = workspace / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Local app instructions\n", encoding="utf-8")
    (workspace / "tasks.yaml").write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "id": "fix-greeting-punctuation",
                        "title": "Fix greeting punctuation",
                        "prompt": "Fix the fixture greeting punctuation.",
                        "category": "runtime",
                        "difficulty": "easy",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    command = agent_command or f'"{Path(sys.executable).as_posix()}" -c "print(\'ok\')"'
    config_path = workspace / "context-eval.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "repo": {"path": repo.as_posix(), "base_ref": "main"},
                "agent": {
                    "name": "local-app-fake-agent",
                    "command": command,
                    "timeout_minutes": 1,
                    "network": "disabled",
                },
                "tasks": "./tasks.yaml",
                "output_dir": "./runs",
                "variants": {
                    "baseline": {
                        "description": "Local app baseline",
                        "overlays": [
                            {
                                "source": "./contexts/baseline/AGENTS.md",
                                "target": "AGENTS.md",
                            }
                        ],
                    }
                },
                "evaluation": {"commands": validation_commands or []},
                "x_unknown": {"preserve": True},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return config_path


def _copy_fixture_repo(tmp_path: Path) -> Path:
    source = Path("examples/fixture-repo")
    fixture = tmp_path / "fixture-repo"
    shutil.copytree(
        source,
        fixture,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
    )
    _run([sys.executable, "setup_fixture_repo.py"], cwd=fixture)
    return fixture


def _write_results(run_dir: Path, rows: list[dict[str, object]]) -> None:
    run_dir.mkdir(parents=True)
    run_dir.joinpath("results.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_local_app_rejects_traversal_for_writes_and_artifact_reads(tmp_path: Path) -> None:
    service = LocalAppService(workspace_root=tmp_path)
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "results.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(LocalAppError, match="path traversal"):
        service.save_config(
            config_path="../context-eval.yaml",
            tasks_path="tasks.yaml",
            config_yaml="repo: {}\n",
            tasks_yaml="tasks: []\n",
        )

    with pytest.raises(LocalAppError, match="path traversal"):
        service.read_artifact(run_dir="runs/run-1", artifact_path="../results.jsonl")

    repo = _create_git_repo(tmp_path / "repo")
    config_path = _write_eval_files(tmp_path, repo)
    unsafe_config = config_path.read_text(encoding="utf-8").replace(
        "tasks: ./tasks.yaml",
        "tasks: ../tasks.yaml",
    )
    with pytest.raises(LocalAppError, match="tasks contains path traversal"):
        service.save_config(
            config_path="context-eval.yaml",
            tasks_path="tasks.yaml",
            config_yaml=unsafe_config,
            tasks_yaml=(tmp_path / "tasks.yaml").read_text(encoding="utf-8"),
        )

    unsafe_output_config = config_path.read_text(encoding="utf-8").replace(
        "output_dir: ./runs",
        "output_dir: ../runs",
    )
    with pytest.raises(LocalAppError, match="output_dir contains path traversal"):
        service.save_config(
            config_path="context-eval.yaml",
            tasks_path="tasks.yaml",
            config_yaml=unsafe_output_config,
            tasks_yaml=(tmp_path / "tasks.yaml").read_text(encoding="utf-8"),
        )


def test_app_command_exposes_loopback_server_options() -> None:
    result = CliRunner().invoke(app, ["app", "--help"])
    command = get_command(app).commands["app"]
    option_names = {
        option
        for parameter in command.params
        for option in getattr(parameter, "opts", [])
    }

    assert result.exit_code == 0
    assert "Start the explicit local app server" in result.output
    assert {"--workspace", "--host", "--port"}.issubset(option_names)


def test_local_app_reports_empty_workspace_and_bootstraps_demo(tmp_path: Path) -> None:
    service = LocalAppService(workspace_root=tmp_path)

    status = service.workspace_state()

    assert status["state"] == "empty"
    assert status["has_config"] is False
    assert status["default_config_path"].endswith("context-eval.yaml")

    bootstrapped = service.bootstrap_demo_workspace()

    assert bootstrapped["state"] == "configured"
    assert bootstrapped["config_path"].endswith("context-eval.yaml")
    assert (tmp_path / "context-eval.yaml").exists()
    assert (tmp_path / "tasks.yaml").exists()
    assert (tmp_path / "demo-repo" / ".git").exists()

    loaded = service.load_config(config_path="context-eval.yaml")
    assert loaded["editable"]["repo"]["path"] == "./demo-repo"
    assert loaded["resolved"]["agents"] == ["demo-agent"]
    assert loaded["resolved"]["variants"] == ["baseline", "experiment"]

    plan = service.plan_run(config_path="context-eval.yaml", cleanup_policy="successful")
    assert plan["case_count"] == 2
    assert {case["variant"] for case in plan["cases"]} == {"baseline", "experiment"}

    started = service.start_run(
        config_path="context-eval.yaml",
        confirm=True,
        cleanup_policy="successful",
    )
    app_run_id = started["app_run_id"]
    deadline = time.time() + 60
    run_status = service.get_run(app_run_id)
    while run_status["status"] in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.1)
        run_status = service.get_run(app_run_id)

    assert run_status["status"] == "completed"
    results = service.results(run_dir=run_status["run_dir"])
    assert results["overview"]["case_count"] == 2
    by_variant = {case["variant"]: case for case in results["cases"]}
    assert by_variant["baseline"]["validation_status"] == "passed"
    assert by_variant["experiment"]["validation_status"] == "passed"
    assert by_variant["baseline"]["hard_evaluation_status"] == "failed"
    assert by_variant["experiment"]["hard_evaluation_status"] == "passed"
    assert by_variant["experiment"]["telemetry_status"] == "collected"
    assert by_variant["experiment"]["total_tokens"] == 180
    assert by_variant["experiment"]["tool_calls_by_name"]["edit_file"] == 1
    assert results["selected_baseline_variant"] == "baseline"
    assert results["available_baseline_variants"] == ["baseline", "experiment"]
    assert results["evaluation_explanation"]["hard_evaluation"]["score_meaning"].startswith(
        "hard score 是通过检查数"
    )
    assert len(results["compare_groups"]) == 1
    compare_group = results["compare_groups"][0]
    assert compare_group["baseline_variant"] == "baseline"
    assert compare_group["comparison_variant"] == "experiment"
    assert compare_group["baseline_case_id"] == by_variant["baseline"]["case_id"]
    assert compare_group["comparison_case_id"] == by_variant["experiment"]["case_id"]
    assert compare_group["experiment_variant"] == "experiment"
    assert compare_group["experiment_case_id"] == by_variant["experiment"]["case_id"]
    assert compare_group["verdict"] == "comparison_improved"
    assert compare_group["hard_delta"] == 1
    assert compare_group["hard_check_delta"] == 1
    assert compare_group["validation_delta"] == 0
    assert compare_group["total_tokens_delta"] == 0
    assert compare_group["evidence_gaps"] == []
    assert compare_group["summary"] == "对比对象 hard checks 改善，validation 状态未变化。"

    detail = service.case_detail(
        run_dir=run_status["run_dir"],
        case_id=by_variant["experiment"]["case_id"],
    )
    assert detail["case"]["variant"] == "experiment"
    assert detail["patch"]["path"].endswith(".patch")
    assert "context-eval-demo" in detail["patch"]["content"]
    assert {item["kind"] for item in detail["logs"]} >= {"agent_stdout", "agent_stderr"}
    assert detail["manual_review"]["decision"] == "not_reviewed"

    saved_review = service.save_manual_review(
        run_dir=run_status["run_dir"],
        case_id=by_variant["experiment"]["case_id"],
        review={
            "decision": "pass",
            "confidence": "high",
            "reviewer": "manual",
            "notes": "Experiment carries the required marker and validation passed.",
        },
    )
    assert saved_review["review"]["decision"] == "pass"
    assert (Path(run_status["run_dir"]) / "manual_reviews.json").exists()

    reviewed_results = service.results(run_dir=run_status["run_dir"])
    reviewed_by_variant = {case["variant"]: case for case in reviewed_results["cases"]}
    assert reviewed_by_variant["experiment"]["manual_review"]["decision"] == "pass"
    reviewed_detail = service.case_detail(
        run_dir=run_status["run_dir"],
        case_id=by_variant["experiment"]["case_id"],
    )
    assert reviewed_detail["manual_review"]["notes"].startswith("Experiment carries")

    exported = json.loads(
        service.export(run_dir=run_status["run_dir"], export_format="json")["content"]
    )
    exported_cases = {case["case_id"]: case for case in exported["cases"]}
    assert exported["manual_reviews"]["reviews"][
        by_variant["experiment"]["case_id"]
    ]["decision"] == "pass"
    assert exported_cases[by_variant["experiment"]["case_id"]]["manual_review"][
        "confidence"
    ] == "high"


def test_local_app_results_compares_selected_baseline_against_other_variants(
    tmp_path: Path,
) -> None:
    service = LocalAppService(workspace_root=tmp_path)
    run_dir = tmp_path / "runs" / "run-compare"
    _write_results(
        run_dir,
        [
            {
                "run_id": "run-compare",
                "case_id": "task-a__baseline__coco",
                "task_id": "task-a",
                "variant": "baseline",
                "repo_ref": "main",
                "agent_name": "coco",
                "network": "disabled",
                "status": "completed",
                "validation_status": "passed",
                "confidence": "high",
                "hard_evaluation_status": "passed",
                "hard_evaluation_score": 2,
                "hard_evaluation_max_score": 2,
                "telemetry_status": "collected",
                "telemetry_source": "json-file",
                "total_tokens": 100,
            },
            {
                "run_id": "run-compare",
                "case_id": "task-a__docs-overlay__coco",
                "task_id": "task-a",
                "variant": "docs-overlay",
                "repo_ref": "main",
                "agent_name": "coco",
                "network": "disabled",
                "status": "completed",
                "validation_status": "skipped",
                "confidence": "low",
                "hard_evaluation_status": "skipped",
                "telemetry_status": "unavailable",
                "telemetry_source": "json-file",
                "telemetry_error": "telemetry file not found: artifacts/telemetry.json",
                "total_tokens": 120,
            },
            {
                "run_id": "run-compare",
                "case_id": "task-a__experiment__coco",
                "task_id": "task-a",
                "variant": "experiment",
                "repo_ref": "main",
                "agent_name": "coco",
                "network": "disabled",
                "status": "validation_failed",
                "validation_status": "failed",
                "confidence": "medium",
                "hard_evaluation_status": "failed",
                "hard_evaluation_score": 1,
                "hard_evaluation_max_score": 2,
                "telemetry_status": "unavailable",
                "telemetry_source": "none",
            },
        ],
    )

    payload = service.results(
        run_dir="runs/run-compare",
        baseline_variant="docs-overlay",
    )

    assert payload["selected_baseline_variant"] == "docs-overlay"
    assert payload["available_baseline_variants"] == [
        "baseline",
        "docs-overlay",
        "experiment",
    ]
    assert payload["baseline_selection_notice"] is None
    groups = {
        (group["baseline_variant"], group["comparison_variant"]): group
        for group in payload["compare_groups"]
    }
    assert set(groups) == {
        ("docs-overlay", "baseline"),
        ("docs-overlay", "experiment"),
    }
    baseline_group = groups[("docs-overlay", "baseline")]
    assert baseline_group["baseline_case_id"] == "task-a__docs-overlay__coco"
    assert baseline_group["comparison_case_id"] == "task-a__baseline__coco"
    assert baseline_group["validation_delta"] == 1
    assert baseline_group["hard_check_delta"] is None
    assert {gap["code"] for gap in baseline_group["evidence_gaps"]} >= {
        "baseline_validation_missing",
        "baseline_hard_evaluation_skipped",
        "baseline_telemetry_missing",
    }
    experiment_group = groups[("docs-overlay", "experiment")]
    assert experiment_group["comparison_variant"] == "experiment"
    assert experiment_group["validation_delta"] == 0
    assert experiment_group["hard_check_delta"] is None
    assert {gap["code"] for gap in experiment_group["evidence_gaps"]} >= {
        "baseline_validation_missing",
        "baseline_hard_evaluation_skipped",
        "baseline_telemetry_missing",
        "comparison_telemetry_missing",
    }


def test_local_app_results_cleans_removed_baseline_selection(tmp_path: Path) -> None:
    service = LocalAppService(workspace_root=tmp_path)
    run_dir = tmp_path / "runs" / "run-compare"
    _write_results(
        run_dir,
        [
            {
                "run_id": "run-compare",
                "case_id": "task-a__baseline__coco",
                "task_id": "task-a",
                "variant": "baseline",
                "repo_ref": "main",
                "agent_name": "coco",
                "network": "disabled",
                "status": "completed",
                "validation_status": "passed",
                "confidence": "high",
            },
            {
                "run_id": "run-compare",
                "case_id": "task-a__experiment__coco",
                "task_id": "task-a",
                "variant": "experiment",
                "repo_ref": "main",
                "agent_name": "coco",
                "network": "disabled",
                "status": "completed",
                "validation_status": "passed",
                "confidence": "high",
            },
        ],
    )

    payload = service.results(
        run_dir="runs/run-compare",
        baseline_variant="removed-variant",
    )

    assert payload["selected_baseline_variant"] == "baseline"
    assert payload["baseline_selection_notice"] == (
        "已清理不存在的比较基线 removed-variant，改用 baseline。"
    )
    assert [
        (group["baseline_variant"], group["comparison_variant"])
        for group in payload["compare_groups"]
    ] == [("baseline", "experiment")]


def test_local_app_initializes_existing_project_without_overwriting(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path / "target-repo")
    service = LocalAppService(workspace_root=tmp_path / "workspace")

    initialized = service.initialize_project_workspace(repo_path=str(repo))

    assert initialized["state"] == "configured"
    loaded = service.load_config(config_path="context-eval.yaml")
    assert loaded["editable"]["repo"]["path"] == repo.as_posix()
    assert loaded["resolved"]["variants"] == ["baseline", "experiment"]
    assert (tmp_path / "workspace" / "tasks.yaml").exists()

    with pytest.raises(LocalAppError, match="refusing to overwrite"):
        service.initialize_project_workspace(repo_path=str(repo))


def test_local_app_save_reloads_and_preserves_raw_unknown_fields(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path / "repo")
    _write_eval_files(tmp_path, repo)
    service = LocalAppService(workspace_root=tmp_path)

    loaded = service.load_config(config_path="context-eval.yaml")
    config_yaml = loaded["config_yaml"].replace("preserve: true", "preserve: edited")
    tasks_yaml = loaded["tasks_yaml"].replace(
        "Fix greeting punctuation",
        "Edited title",
    ).replace(
        "difficulty: easy",
        "difficulty: medium\n  x_task_unknown:\n    keep: true",
    )
    saved = service.save_config(
        config_path="context-eval.yaml",
        tasks_path="tasks.yaml",
        config_yaml=config_yaml,
        tasks_yaml=tasks_yaml,
    )

    assert saved["config_path"].endswith("context-eval.yaml")
    assert saved["tasks_path"].endswith("tasks.yaml")
    assert saved["reloaded"]["editable"]["tasks"][0]["title"] == "Edited title"
    assert saved["reloaded"]["editable"]["tasks"][0]["difficulty"] == "medium"
    assert "x_task_unknown" in saved["reloaded"]["tasks_yaml"]
    assert "preserve: edited" in (tmp_path / "context-eval.yaml").read_text(encoding="utf-8")
    assert "Edited title" in (tmp_path / "tasks.yaml").read_text(encoding="utf-8")
    assert "x_task_unknown" in (tmp_path / "tasks.yaml").read_text(encoding="utf-8")


def test_local_app_saves_editable_tasks_without_rewriting_config_unknowns(
    tmp_path: Path,
) -> None:
    repo = _create_git_repo(tmp_path / "repo")
    _write_eval_files(tmp_path, repo)
    service = LocalAppService(workspace_root=tmp_path)

    loaded = service.load_config(config_path="context-eval.yaml")
    editable = loaded["editable"]
    task = editable["tasks"][0]
    task["prompt"] = "Update README with the saved editor marker."
    task["expected_outcome"] = {
        "summary": "README contains saved editor marker.",
        "acceptance_points": ["The saved editor marker is present."],
        "files": [{"path": "README.md", "must_change": True}],
    }
    task["validation_commands"] = ["python -m pytest"]
    task["hard_evaluation"] = {
        "enabled": True,
        "require_validation_pass": False,
        "command_checks": [
            {
                "label": "readme-marker",
                "command": "python -c \"print('saved editor marker')\"",
                "expected": "saved editor marker",
            }
        ],
    }
    task["soft_evaluation"] = {
        "enabled": True,
        "mode": "payload-only",
        "rubric": [
            {
                "name": "task-fit",
                "description": "Patch satisfies the task.",
                "weight": 1,
            }
        ],
    }

    saved = service.save_editable_config(
        config_path="context-eval.yaml",
        tasks_path="tasks.yaml",
        editable=editable,
    )

    config_text = (tmp_path / "context-eval.yaml").read_text(encoding="utf-8")
    tasks_text = (tmp_path / "tasks.yaml").read_text(encoding="utf-8")
    assert "x_unknown" in config_text
    assert "saved editor marker" in tasks_text
    assert "command_checks" in tasks_text
    assert saved["reloaded"]["editable"]["tasks"][0]["expected_outcome"]["summary"] == (
        "README contains saved editor marker."
    )

    plan = service.plan_run(config_path="context-eval.yaml", cleanup_policy="successful")
    assert plan["cases"][0]["expected_outcome_summary"] == (
        "README contains saved editor marker."
    )


def test_local_app_saves_editable_variants_and_agent_profiles(
    tmp_path: Path,
) -> None:
    repo = _create_git_repo(tmp_path / "repo")
    _write_eval_files(tmp_path, repo)
    config_path = tmp_path / "context-eval.yaml"
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    primary_agent = config_data.pop("agent")
    primary_agent["kind"] = "custom"
    primary_agent["telemetry"] = {"collector": "json-file", "file": "telemetry.json"}
    config_data["agents"] = {
        "local-app-fake-agent": primary_agent,
        "backup-agent": {
            "kind": "custom",
            "command": f'"{Path(sys.executable).as_posix()}" -c "print(\'backup\')"',
            "timeout_minutes": 1,
            "network": "disabled",
        },
    }
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
    service = LocalAppService(workspace_root=tmp_path)

    loaded = service.load_config(config_path="context-eval.yaml")
    editable = loaded["editable"]
    editable["variants"][0]["description"] = "Edited structured baseline"
    editable["variants"][0]["overlays"] = [
        {"source": "./contexts/baseline/AGENTS.md", "target": "docs/AGENTS.md"}
    ]
    editable["agent"] = {
        **editable["agents"][0],
        "command": f'"{Path(sys.executable).as_posix()}" -c "print(\'edited\')"',
        "timeout_minutes": 2,
        "network": "enabled",
    }
    editable["agents"][0] = editable["agent"]
    editable["agents"][1] = {
        **editable["agents"][1],
        "kind": "codex-cli",
        "command": "codex exec \"{prompt_file}\"",
        "timeout_minutes": 3,
    }

    saved = service.save_editable_config(
        config_path="context-eval.yaml",
        tasks_path="tasks.yaml",
        editable=editable,
    )

    saved_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved_config["x_unknown"] == {"preserve": True}
    assert saved_config["variants"]["baseline"]["description"] == (
        "Edited structured baseline"
    )
    assert saved_config["variants"]["baseline"]["overlays"] == [
        {"source": "./contexts/baseline/AGENTS.md", "target": "docs/AGENTS.md"}
    ]
    assert saved_config["agents"]["local-app-fake-agent"]["network"] == "enabled"
    assert saved_config["agents"]["local-app-fake-agent"]["telemetry"] == {
        "collector": "json-file",
        "file": "telemetry.json",
    }
    assert saved_config["agents"]["backup-agent"]["kind"] == "codex-cli"
    assert saved["reloaded"]["editable"]["variants"][0]["description"] == (
        "Edited structured baseline"
    )


def test_local_app_save_rejects_overlay_paths_outside_workspace(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path / "repo")
    config_path = _write_eval_files(tmp_path, repo)
    outside_source = tmp_path.parent / "outside-overlay.md"
    outside_source.write_text("# outside\n", encoding="utf-8")
    service = LocalAppService(workspace_root=tmp_path)
    loaded = service.load_config(config_path="context-eval.yaml")

    traversal_config = loaded["config_yaml"].replace(
        "source: ./contexts/baseline/AGENTS.md",
        "source: ../outside-overlay.md",
    )
    with pytest.raises(LocalAppError, match="overlay source contains path traversal"):
        service.save_config(
            config_path="context-eval.yaml",
            tasks_path="tasks.yaml",
            config_yaml=traversal_config,
            tasks_yaml=loaded["tasks_yaml"],
        )

    absolute_config = loaded["config_yaml"].replace(
        "source: ./contexts/baseline/AGENTS.md",
        f"source: {outside_source.as_posix()}",
    )
    with pytest.raises(LocalAppError, match="overlay source must stay inside"):
        service.save_config(
            config_path="context-eval.yaml",
            tasks_path="tasks.yaml",
            config_yaml=absolute_config,
            tasks_yaml=loaded["tasks_yaml"],
        )

    target_traversal_config = loaded["config_yaml"].replace(
        "target: AGENTS.md",
        "target: ../AGENTS.md",
    )
    with pytest.raises(LocalAppError, match="overlay target contains path traversal"):
        service.save_config(
            config_path="context-eval.yaml",
            tasks_path="tasks.yaml",
            config_yaml=target_traversal_config,
            tasks_yaml=loaded["tasks_yaml"],
        )

    target_absolute_config = loaded["config_yaml"].replace(
        "target: AGENTS.md",
        f"target: {outside_source.as_posix()}",
    )
    with pytest.raises(LocalAppError, match="overlay target must be a safe relative path"):
        service.save_config(
            config_path="context-eval.yaml",
            tasks_path="tasks.yaml",
            config_yaml=target_absolute_config,
            tasks_yaml=loaded["tasks_yaml"],
        )

    assert config_path.read_text(encoding="utf-8") == loaded["config_yaml"]


def test_local_app_preflight_is_side_effect_free(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path / "repo")
    agent_sentinel = tmp_path / "agent-ran.txt"
    validation_sentinel = tmp_path / "validation-ran.txt"
    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        f"from pathlib import Path\nPath({str(agent_sentinel)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    validation_script = tmp_path / "validate.py"
    validation_script.write_text(
        f"from pathlib import Path\nPath({str(validation_sentinel)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    _write_eval_files(
        tmp_path,
        repo,
        agent_command=f'"{Path(sys.executable).as_posix()}" "{agent_script}"',
        validation_commands=[f'"{Path(sys.executable).as_posix()}" "{validation_script}"'],
    )
    service = LocalAppService(workspace_root=tmp_path)

    result = service.preflight(config_path="context-eval.yaml", check_agents=True)

    assert result["ok"] is True
    assert "side_effect_free" in result["checks"]
    assert not agent_sentinel.exists()
    assert not validation_sentinel.exists()
    assert not (tmp_path / "runs").exists()


def test_local_app_plans_runs_and_executes_fixture_workflow(tmp_path: Path) -> None:
    fixture = _copy_fixture_repo(tmp_path)
    python_exe = Path(sys.executable).as_posix()
    _write_eval_files(
        tmp_path,
        fixture,
        agent_command=f'"{python_exe}" scripts/example_agent.py "{{prompt_file}}"',
        validation_commands=[f'"{python_exe}" -m pytest'],
    )
    service = LocalAppService(workspace_root=tmp_path)

    plan = service.plan_run(config_path="context-eval.yaml", cleanup_policy="successful")
    assert plan["case_count"] == 1
    assert plan["cases"][0]["agent_name"] == "local-app-fake-agent"
    assert plan["output_dir"].endswith("runs")

    started = service.start_run(
        config_path="context-eval.yaml",
        confirm=True,
        cleanup_policy="successful",
    )
    app_run_id = started["app_run_id"]
    deadline = time.time() + 60
    status = service.get_run(app_run_id)
    while status["status"] in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.1)
        status = service.get_run(app_run_id)

    assert status["status"] == "completed"
    assert status["completed_cases"] == 1
    assert status["run_dir"]

    results = service.results(run_dir=status["run_dir"])
    assert results["overview"]["case_count"] == 1
    assert results["cases"][0]["status"] == "completed"
    assert results["cases"][0]["validation_status"] == "passed"

    logs = service.run_logs(app_run_id)
    assert "Running agent=local-app-fake-agent" in "\n".join(logs["console"])

    export = service.export(run_dir=status["run_dir"], export_format="json")
    payload = json.loads(export["content"])
    assert payload["case_count"] == 1


def test_local_app_run_scope_filters_plan_and_execution(tmp_path: Path) -> None:
    fixture = _copy_fixture_repo(tmp_path)
    python_exe = Path(sys.executable).as_posix()
    _write_eval_files(
        tmp_path,
        fixture,
        agent_command=f'"{python_exe}" scripts/example_agent.py "{{prompt_file}}"',
        validation_commands=[f'"{python_exe}" -m pytest'],
    )
    config_path = tmp_path / "context-eval.yaml"
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    primary_agent = config_data.pop("agent")
    primary_agent["kind"] = "custom"
    config_data["agents"] = {
        "first-agent": primary_agent,
        "second-agent": {
            **primary_agent,
            "command": f'"{python_exe}" scripts/example_agent.py "{{prompt_file}}"',
        },
    }
    config_data["variants"]["experiment"] = {
        "description": "Experiment scope",
        "overlays": [
            {"source": "./contexts/baseline/AGENTS.md", "target": "AGENTS.md"}
        ],
    }
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
    tasks_path = tmp_path / "tasks.yaml"
    tasks_data = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    second_task = dict(tasks_data["tasks"][0])
    second_task["id"] = "second-task"
    second_task["prompt"] = "Fix the fixture greeting punctuation again."
    tasks_data["tasks"].append(second_task)
    tasks_path.write_text(yaml.safe_dump(tasks_data, sort_keys=False), encoding="utf-8")
    service = LocalAppService(workspace_root=tmp_path)

    plan = service.plan_run(
        config_path="context-eval.yaml",
        cleanup_policy="successful",
        agents=["second-agent"],
        variants=["experiment"],
        task_ids=["second-task"],
    )

    assert plan["case_count"] == 1
    assert plan["agents"] == ["second-agent"]
    assert plan["variants"] == ["experiment"]
    assert plan["tasks"] == ["second-task"]

    started = service.start_run(
        config_path="context-eval.yaml",
        confirm=True,
        cleanup_policy="successful",
        agents=["second-agent"],
        variants=["experiment"],
        task_ids=["second-task"],
    )
    app_run_id = started["app_run_id"]
    deadline = time.time() + 60
    status = service.get_run(app_run_id)
    while status["status"] in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.1)
        status = service.get_run(app_run_id)

    assert status["status"] == "completed"
    assert status["case_count"] == 1
    results = service.results(run_dir=status["run_dir"])
    assert results["overview"]["case_count"] == 1
    result = results["cases"][0]
    assert result["agent_name"] == "second-agent"
    assert result["task_id"] == "second-task"
    assert result["variant"] == "experiment"


def test_local_app_plan_and_results_include_hybrid_evaluation(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path / "repo")
    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "from pathlib import Path\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'fixed marker\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Hybrid instructions\n", encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "id": "hybrid-task",
                        "prompt": "Add the fixed marker.",
                        "expected_outcome": {
                            "summary": "README contains fixed marker.",
                            "acceptance_points": ["The fixed marker is present."],
                        },
                        "hard_evaluation": {
                            "enabled": True,
                            "require_validation_pass": False,
                            "required_paths": ["README.md"],
                            "expected_snippets": [
                                {"path": "README.md", "snippets": ["fixed marker"]}
                            ],
                        },
                        "soft_evaluation": {
                            "enabled": True,
                            "mode": "payload-only",
                            "rubric": [
                                {
                                    "name": "quality",
                                    "weight": 1,
                                    "description": "Patch is clear.",
                                }
                            ],
                        },
                        "x_unknown_task_field": "keep-me",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "repo": {"path": repo.as_posix(), "base_ref": "main"},
                "agents": {
                    "coco": {
                        "kind": "coco",
                        "command": (
                            f'"{Path(sys.executable).as_posix()}" '
                            f'"{agent_script.as_posix()}"'
                        ),
                        "timeout_minutes": 1,
                        "network": "disabled",
                    }
                },
                "tasks": "./tasks.yaml",
                "output_dir": "./runs",
                "variants": {
                    "baseline": {
                        "description": "Hybrid baseline",
                        "overlays": [
                            {
                                "source": "./contexts/baseline/AGENTS.md",
                                "target": "AGENTS.md",
                            }
                        ],
                    }
                },
                "evaluation": {"commands": []},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    service = LocalAppService(workspace_root=tmp_path)

    loaded = service.load_config(config_path="context-eval.yaml")
    assert "x_unknown_task_field" in loaded["tasks_yaml"]
    plan = service.plan_run(config_path="context-eval.yaml", cleanup_policy="never")
    case = plan["cases"][0]
    assert case["agent_name"] == "coco"
    assert case["agent_kind"] == "coco"
    assert case["expected_outcome_summary"] == "README contains fixed marker."
    assert case["hard_evaluation_enabled"] is True
    assert case["soft_evaluation_enabled"] is True

    started = service.start_run(
        config_path="context-eval.yaml",
        confirm=True,
        cleanup_policy="never",
    )
    app_run_id = started["app_run_id"]
    deadline = time.time() + 60
    status = service.get_run(app_run_id)
    while status["status"] in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.1)
        status = service.get_run(app_run_id)

    results = service.results(run_dir=status["run_dir"])
    result_case = results["cases"][0]
    assert result_case["hard_evaluation_status"] == "passed"
    assert result_case["hard_evaluation_score"] == result_case["hard_evaluation_max_score"]
    assert result_case["soft_evaluation_status"] == "payload_generated"
    assert result_case["hard_evaluation"]["passed"] is True
    assert result_case["soft_evaluation"]["payload_path"].endswith(
        "soft_evaluation_payload.json"
    )

    hard_artifact = service.read_artifact(
        run_dir=status["run_dir"],
        artifact_path=result_case["hard_evaluation_path"],
    )
    assert '"passed": true' in hard_artifact["content"]


def test_local_app_results_rejects_unsafe_hard_evaluation_path(tmp_path: Path) -> None:
    service = LocalAppService(workspace_root=tmp_path)
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    secret = tmp_path / "secret-hard-evaluation.json"
    secret.write_text('{"leaked": true}\n', encoding="utf-8")
    result = {
        "run_id": "run-1",
        "case_id": "task-a__baseline",
        "task_id": "task-a",
        "variant": "baseline",
        "repo_ref": "main",
        "agent_name": "coco",
        "network": "disabled",
        "status": "completed",
        "hard_evaluation_status": "passed",
        "hard_evaluation_path": "../../secret-hard-evaluation.json",
    }
    (run_dir / "results.jsonl").write_text(json.dumps(result) + "\n", encoding="utf-8")

    payload = service.results(run_dir="runs/run-1")
    hard_evaluation = payload["cases"][0]["hard_evaluation"]

    assert hard_evaluation["path"] == "../../secret-hard-evaluation.json"
    assert "path traversal" in hard_evaluation["error"]
    assert "leaked" not in hard_evaluation
