"""Install built release artifacts and run a local fixture smoke."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


NETWORK_PATTERNS = (
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "EventSource",
    "sendBeacon",
    "http://",
    "https://",
)


def _display_command(command: list[str]) -> str:
    display = ["python" if item == sys.executable else item for item in command]
    if len(display) >= 3 and display[1:3] == ["-m", "pip"]:
        display[0] = "python"
    return " ".join(display)


def _quote(value: Path | str) -> str:
    return subprocess.list2cmdline([str(value)])


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _console_script(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "context-eval.exe"
    return venv_dir / "bin" / "context-eval"


def _find_wheel(dist_dir: Path) -> tuple[Path | None, list[str]]:
    if not dist_dir.is_dir():
        return None, [f"{dist_dir}: not a directory"]

    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        return None, [f"{dist_dir}: missing wheel artifact"]
    if len(wheels) > 1:
        names = ", ".join(path.name for path in wheels)
        return None, [f"{dist_dir}: expected exactly one wheel artifact, found {names}"]
    return wheels[0], []


def _run(command: list[str], *, cwd: Path, timeout_seconds: int = 180) -> int:
    print(f"Running: {_display_command(command)}")
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    if result.returncode == 0:
        return 0

    print(f"error: command failed with exit code {result.returncode}", file=sys.stderr)
    print(f"command: {_display_command(command)}", file=sys.stderr)
    if result.stdout:
        print("stdout:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
    if result.stderr:
        print("stderr:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return result.returncode


def _copy_fixture(root: Path, work_dir: Path) -> Path:
    source = root / "examples" / "fixture-repo"
    fixture = work_dir / "fixture-repo"
    shutil.copytree(
        source,
        fixture,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
    )
    return fixture


def _write_smoke_files(work_dir: Path, fixture: Path, smoke_python: Path) -> Path:
    context_dir = work_dir / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Release candidate smoke\n", encoding="utf-8")

    tasks_path = work_dir / "tasks.yaml"
    tasks_path.write_text(
        json.dumps(
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
            indent=2,
        ),
        encoding="utf-8",
    )

    validation_command = subprocess.list2cmdline(
        [
            str(smoke_python),
            "-c",
            "from fixture_app.greetings import greet; assert greet('world') == 'Hello, world!'",
        ]
    )
    config_path = work_dir / "context-eval.yaml"
    config_path.write_text(
        json.dumps(
            {
                "repo": {
                    "path": fixture.as_posix(),
                    "base_ref": "main",
                },
                "agent": {
                    "name": "release-candidate-fake-agent",
                    "command": (
                        f"{_quote(smoke_python)} scripts/example_agent.py "
                        '"{prompt_file}"'
                    ),
                    "timeout_minutes": 1,
                    "network": "disabled",
                },
                "tasks": tasks_path.as_posix(),
                "output_dir": (work_dir / "runs").as_posix(),
                "variants": {
                    "baseline": {
                        "description": "Release candidate install smoke baseline",
                        "overlays": [
                            {
                                "source": (context_dir / "AGENTS.md").as_posix(),
                                "target": "AGENTS.md",
                            }
                        ],
                    }
                },
                "evaluation": {
                    "commands": [validation_command],
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return config_path


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _assert_no_network_calls(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [f"{path.name}: contains network pattern {pattern}" for pattern in NETWORK_PATTERNS if pattern in text]


def _validate_artifacts(work_dir: Path, run_dir: Path) -> list[str]:
    summary_csv = work_dir / "summary.csv"
    summary_json = work_dir / "summary.json"
    ui_html = work_dir / "context-eval-ui.html"
    required = [
        run_dir / "results.jsonl",
        run_dir / "run_manifest.json",
        run_dir / "report.md",
        summary_csv,
        summary_json,
        ui_html,
    ]
    errors = [f"missing smoke artifact: {path}" for path in required if not path.exists()]
    if errors:
        return errors

    try:
        results = _read_jsonl(run_dir / "results.jsonl")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"results.jsonl is not parseable: {exc}")
        results = []
    if len(results) != 1:
        errors.append(f"results.jsonl should contain one row, found {len(results)}")
    elif results[0].get("status") != "completed":
        errors.append(f"smoke result did not complete: {results[0].get('status')}")
    elif results[0].get("validation_status") != "passed":
        errors.append(f"smoke validation did not pass: {results[0].get('validation_status')}")

    try:
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"run_manifest.json is not parseable: {exc}")
    else:
        if manifest.get("case_count") != 1:
            errors.append(f"run_manifest.json should record one case, found {manifest.get('case_count')}")

    try:
        csv_rows = list(csv.DictReader(summary_csv.read_text(encoding="utf-8").splitlines()))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        errors.append(f"summary.csv is not parseable: {exc}")
    else:
        if len(csv_rows) != 1:
            errors.append(f"summary.csv should contain one row, found {len(csv_rows)}")

    try:
        summary = json.loads(summary_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"summary.json is not parseable: {exc}")
    else:
        if summary.get("case_count") != 1:
            errors.append(f"summary.json should record one case, found {summary.get('case_count')}")

    for artifact in [run_dir / "report.md", summary_csv, summary_json, ui_html]:
        errors.extend(_assert_no_network_calls(artifact))

    return errors


def _dry_run(wheel: Path, root: Path) -> int:
    print("DRY RUN: would create temporary Python environment")
    print(
        "DRY RUN: would run "
        f"python -m pip install --no-deps --force-reinstall {wheel}"
    )
    print(f"DRY RUN: would copy {(root / 'examples' / 'fixture-repo').as_posix()}")
    print("DRY RUN: would run context-eval validate-config --config <temp>/context-eval.yaml")
    print("DRY RUN: would run context-eval run --config <temp>/context-eval.yaml")
    print("DRY RUN: would run context-eval report <temp>/runs/<run-id>")
    print("DRY RUN: would run context-eval export <temp>/runs/<run-id> --format csv")
    print("DRY RUN: would run context-eval export <temp>/runs/<run-id> --format json")
    print("DRY RUN: would run context-eval ui --config <temp>/context-eval.yaml")
    return 0


def _run_smoke(root: Path, wheel: Path, work_dir: Path) -> int:
    venv_dir = work_dir / "venv"
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(venv_dir)
    smoke_python = _venv_python(venv_dir)
    context_eval = _console_script(venv_dir)

    install_command = [
        str(smoke_python),
        "-m",
        "pip",
        "install",
        "--no-deps",
        "--force-reinstall",
        str(wheel),
    ]
    exit_code = _run(install_command, cwd=work_dir)
    if exit_code != 0:
        return exit_code

    fixture = _copy_fixture(root, work_dir)
    exit_code = _run([sys.executable, "setup_fixture_repo.py"], cwd=fixture)
    if exit_code != 0:
        return exit_code

    config_path = _write_smoke_files(work_dir, fixture, smoke_python)
    commands = [
        [str(context_eval), "validate-config", "--config", str(config_path)],
        [
            str(context_eval),
            "run",
            "--config",
            str(config_path),
            "--cleanup-policy",
            "successful",
        ],
    ]
    for command in commands:
        exit_code = _run(command, cwd=work_dir)
        if exit_code != 0:
            return exit_code

    run_dirs = sorted(path for path in (work_dir / "runs").iterdir() if path.is_dir())
    if len(run_dirs) != 1:
        print(f"error: expected one run directory, found {len(run_dirs)}", file=sys.stderr)
        return 1
    run_dir = run_dirs[0]

    summary_csv = work_dir / "summary.csv"
    summary_json = work_dir / "summary.json"
    ui_html = work_dir / "context-eval-ui.html"
    commands = [
        [str(context_eval), "report", str(run_dir)],
        [str(context_eval), "export", str(run_dir), "--format", "csv", "--output", str(summary_csv)],
        [str(context_eval), "export", str(run_dir), "--format", "json", "--output", str(summary_json)],
        [
            str(context_eval),
            "ui",
            "--config",
            str(config_path),
            "--run-dir",
            str(run_dir),
            "--output",
            str(ui_html),
        ],
    ]
    for command in commands:
        exit_code = _run(command, cwd=work_dir)
        if exit_code != 0:
            return exit_code

    errors = _validate_artifacts(work_dir, run_dir)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Release candidate install smoke passed: {wheel.name}")
    return 0


def run_install_smoke(
    *,
    root: Path,
    dist_dir: Path,
    work_dir: Path | None,
    dry_run: bool,
) -> int:
    root = root.resolve()
    dist_dir = dist_dir.resolve()
    wheel, errors = _find_wheel(dist_dir)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    assert wheel is not None

    if dry_run:
        return _dry_run(wheel, root)

    if work_dir is not None:
        work_dir = work_dir.resolve()
        if work_dir.exists() and any(work_dir.iterdir()):
            print(f"error: work directory must be empty: {work_dir}", file=sys.stderr)
            return 1
        work_dir.mkdir(parents=True, exist_ok=True)
        return _run_smoke(root, wheel, work_dir)

    with tempfile.TemporaryDirectory(prefix="context-eval-install-smoke-") as temporary:
        return _run_smoke(root, wheel, Path(temporary))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=Path.cwd(),
        type=Path,
        help="Repository root that provides local fixture inputs. Defaults to the current directory.",
    )
    parser.add_argument(
        "--dist-dir",
        required=True,
        type=Path,
        help="Directory containing built wheel and sdist artifacts.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Optional empty work directory to preserve smoke artifacts for debugging.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the local install smoke plan without creating environments or artifacts.",
    )
    args = parser.parse_args(argv)

    return run_install_smoke(
        root=args.root,
        dist_dir=args.dist_dir,
        work_dir=args.work_dir,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
