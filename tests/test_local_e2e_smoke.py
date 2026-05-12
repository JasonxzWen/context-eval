from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.local_e2e


def _context_eval_command() -> list[str]:
    script_name = "context-eval.exe" if sys.platform == "win32" else "context-eval"
    venv_script = Path(sys.executable).with_name(script_name)
    if venv_script.exists():
        return [str(venv_script)]

    resolved = shutil.which("context-eval")
    if resolved:
        return [resolved]

    pytest.fail(
        "context-eval console script was not found; install the package before "
        "running the local-e2e smoke"
    )


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


def _write_smoke_config(tmp_path: Path, fixture: Path) -> Path:
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Local smoke instructions\n", encoding="utf-8")

    tasks_path = tmp_path / "tasks.yaml"
    tasks_path.write_text(
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

    python_exe = Path(sys.executable).as_posix()
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "repo": {
                    "path": fixture.as_posix(),
                    "base_ref": "main",
                },
                "agent": {
                    "name": "local-e2e-fake-agent",
                    "command": f'"{python_exe}" scripts/example_agent.py "{{prompt_file}}"',
                    "timeout_minutes": 1,
                    "network": "disabled",
                },
                "tasks": tasks_path.as_posix(),
                "output_dir": (tmp_path / "runs").as_posix(),
                "variants": {
                    "baseline": {
                        "description": "Local smoke baseline",
                        "overlays": [
                            {
                                "source": (context_dir / "AGENTS.md").as_posix(),
                                "target": "AGENTS.md",
                            }
                        ],
                    }
                },
                "evaluation": {
                    "commands": [f'"{python_exe}" -m pytest'],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return config_path


def _assert_no_network_calls(text: str) -> None:
    for forbidden in [
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "sendBeacon",
        "http://",
        "https://",
    ]:
        assert forbidden not in text


def test_installed_cli_local_e2e_smoke_uses_only_fixture_artifacts(tmp_path: Path) -> None:
    cli = _context_eval_command()
    fixture = _copy_fixture_repo(tmp_path)
    config_path = _write_smoke_config(tmp_path, fixture)

    _run(
        [
            *cli,
            "run",
            "--config",
            str(config_path),
            "--cleanup-policy",
            "successful",
        ],
        cwd=tmp_path,
    )

    run_dirs = sorted((tmp_path / "runs").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    _run([*cli, "report", str(run_dir)], cwd=tmp_path)

    summary_csv = tmp_path / "summary.csv"
    summary_json = tmp_path / "summary.json"
    ui_html = tmp_path / "context-eval-ui.html"
    _run(
        [*cli, "export", str(run_dir), "--format", "csv", "--output", str(summary_csv)],
        cwd=tmp_path,
    )
    _run(
        [*cli, "export", str(run_dir), "--format", "json", "--output", str(summary_json)],
        cwd=tmp_path,
    )
    _run(
        [
            *cli,
            "ui",
            "--config",
            str(config_path),
            "--run-dir",
            str(run_dir),
            "--output",
            str(ui_html),
        ],
        cwd=tmp_path,
    )

    for artifact in [
        run_dir / "results.jsonl",
        run_dir / "run_manifest.json",
        run_dir / "report.md",
        summary_csv,
        summary_json,
        ui_html,
    ]:
        assert artifact.exists()

    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(results) == 1
    result = results[0]
    assert result["agent_name"] == "local-e2e-fake-agent"
    assert result["network"] == "disabled"
    assert result["status"] == "completed"
    assert result["validation_status"] == "passed"
    assert result["telemetry_status"] == "unavailable"
    assert result["telemetry_source"] == "none"
    assert result["prompt_tokens"] is None
    assert result["completion_tokens"] is None
    assert result["total_tokens"] is None
    assert result["tool_call_count"] is None
    assert result["tool_calls_by_name"] == {}
    assert result["cleanup_status"] == "succeeded"
    assert result["workspace_retained"] is False

    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["case_count"] == 1
    assert manifest["cleanup_policy"] == "successful"
    assert manifest["tasks"][0]["id"] == "fix-greeting-punctuation"
    assert manifest["variants"][0]["name"] == "baseline"

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "context-eval evaluates the effect of context variants" in report
    assert "not the absolute capability of an agent" in report
    assert "Telemetry Summary" in report

    csv_rows = list(csv.DictReader(summary_csv.read_text(encoding="utf-8").splitlines()))
    assert len(csv_rows) == 1
    assert csv_rows[0]["telemetry_status"] == "unavailable"
    assert csv_rows[0]["total_tokens"] == ""
    assert csv_rows[0]["tool_calls_by_name"] == ""

    export = json.loads(summary_json.read_text(encoding="utf-8"))
    assert export["case_count"] == 1
    assert export["cases"][0]["total_tokens"] is None
    assert export["cases"][0]["tool_calls_by_name"] == {}

    html = ui_html.read_text(encoding="utf-8")
    assert "context-eval local UI" in html
    assert "local-e2e-fake-agent" in html
    assert "fix-greeting-punctuation" in html

    for artifact_text in [
        report,
        summary_csv.read_text(encoding="utf-8"),
        summary_json.read_text(encoding="utf-8"),
        html,
    ]:
        _assert_no_network_calls(artifact_text)
