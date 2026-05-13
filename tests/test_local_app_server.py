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


def test_app_command_exposes_loopback_server_options() -> None:
    result = CliRunner().invoke(app, ["app", "--help"])

    assert result.exit_code == 0
    assert "Start the explicit local app server" in result.output
    assert "--workspace" in result.output
    assert "--host" in result.output
    assert "--port" in result.output


def test_local_app_save_load_preserves_raw_unknown_config_fields(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path / "repo")
    _write_eval_files(tmp_path, repo)
    service = LocalAppService(workspace_root=tmp_path)

    loaded = service.load_config(config_path="context-eval.yaml")
    config_yaml = loaded["config_yaml"].replace("preserve: true", "preserve: edited")
    tasks_yaml = loaded["tasks_yaml"].replace("Fix greeting punctuation", "Edited title")
    saved = service.save_config(
        config_path="context-eval.yaml",
        tasks_path="tasks.yaml",
        config_yaml=config_yaml,
        tasks_yaml=tasks_yaml,
    )

    assert saved["config_path"].endswith("context-eval.yaml")
    assert saved["tasks_path"].endswith("tasks.yaml")
    assert "preserve: edited" in (tmp_path / "context-eval.yaml").read_text(encoding="utf-8")
    assert "Edited title" in (tmp_path / "tasks.yaml").read_text(encoding="utf-8")


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
