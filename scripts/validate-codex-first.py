"""Run the deterministic Codex-first validation gate."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PYTHON_TESTS = [
    "tests/test_adapters.py::test_codex_jsonl_collector_saves_stdout_and_normalizes_usage",
    "tests/test_adapters.py::test_codex_jsonl_collector_reports_missing_usage_as_partial",
    "tests/test_adapters.py::test_codex_jsonl_collector_reports_invalid_jsonl_as_error",
    "tests/test_runner.py::test_runner_records_codex_jsonl_artifacts_and_telemetry",
    "tests/test_local_app_server.py::test_local_app_preflight_reports_codex_profile_diagnostics",
    "tests/test_local_app_server.py::test_local_app_reports_empty_workspace_and_bootstraps_demo",
    "tests/test_project_readiness.py::test_local_app_harness_readiness_documents_codex_first_gate",
]

PLAYWRIGHT_TEST = "empty workspace starts at first-run choices and bootstraps demo"


def _command(name: str) -> str:
    if os.name == "nt":
        return f"{name}.cmd"
    return name


def _run(
    label: str,
    args: list[str],
    *,
    cwd: Path,
    evidence_dir: Path,
    env: dict[str, str] | None = None,
) -> None:
    log_path = evidence_dir / f"{label}.log"
    merged_env = os.environ.copy()
    merged_env.setdefault("PYTHONUTF8", "1")
    if env:
        merged_env.update(env)

    print(f"+ {' '.join(args)}")
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"+ {' '.join(args)}\n")
        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
        code = process.wait()
        if code != 0:
            raise subprocess.CalledProcessError(code, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic Codex-first backend and browser validation."
    )
    parser.add_argument(
        "--install-frontend",
        action="store_true",
        help="Run npm ci in frontend/ before validation.",
    )
    parser.add_argument(
        "--install-browsers",
        action="store_true",
        help="Install the Chromium browser required by Playwright.",
    )
    parser.add_argument(
        "--install-system-deps",
        action="store_true",
        help="On Linux, ask Playwright to install browser system dependencies.",
    )
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Run only the Python Codex-first contracts.",
    )
    parser.add_argument(
        "--live-codex",
        action="store_true",
        help="Also check that the local Codex CLI exposes noninteractive exec help.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Directory for command logs and Playwright artifacts.",
    )
    return parser.parse_args()


def _evidence_dir(repo_root: Path, requested: Path | None) -> Path:
    if requested is not None:
        evidence_dir = requested
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        evidence_dir = repo_root / ".context-eval" / "verification" / "codex-first" / stamp
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return evidence_dir


def _run_live_codex_check(evidence_dir: Path) -> None:
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("live Codex smoke requested, but `codex` was not found on PATH")
    _run(
        "live-codex-version",
        [codex, "--version"],
        cwd=evidence_dir,
        evidence_dir=evidence_dir,
    )
    _run(
        "live-codex-exec-help",
        [codex, "exec", "--help"],
        cwd=evidence_dir,
        evidence_dir=evidence_dir,
    )


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    frontend_dir = repo_root / "frontend"
    evidence_dir = _evidence_dir(repo_root, args.evidence_dir)

    print(f"Codex-first evidence: {evidence_dir}")

    _run(
        "python-contracts",
        [
            sys.executable,
            "-m",
            "pytest",
            *PYTHON_TESTS,
            "-q",
            "--basetemp",
            str(evidence_dir / "pytest-tmp"),
        ],
        cwd=repo_root,
        evidence_dir=evidence_dir,
    )

    if not args.skip_browser:
        npm = _command("npm")
        npx = _command("npx")
        if args.install_frontend:
            _run("frontend-npm-ci", [npm, "ci"], cwd=frontend_dir, evidence_dir=evidence_dir)
        if args.install_browsers:
            browser_args = [npx, "playwright", "install"]
            if args.install_system_deps and platform.system() == "Linux":
                browser_args.append("--with-deps")
            browser_args.append("chromium")
            _run(
                "frontend-playwright-install",
                browser_args,
                cwd=frontend_dir,
                evidence_dir=evidence_dir,
            )

        frontend_env = {
            "CONTEXT_EVAL_PYTHON": sys.executable,
            "CONTEXT_EVAL_EVIDENCE_DIR": str(evidence_dir),
            "PLAYWRIGHT_PORT": "4187",
        }
        _run(
            "frontend-typecheck",
            [npm, "run", "typecheck"],
            cwd=frontend_dir,
            evidence_dir=evidence_dir,
            env=frontend_env,
        )
        _run(
            "frontend-build",
            [npm, "run", "build"],
            cwd=frontend_dir,
            evidence_dir=evidence_dir,
            env=frontend_env,
        )
        _run(
            "frontend-codex-first-e2e",
            [
                npx,
                "playwright",
                "test",
                "app-shell.spec.ts",
                "-g",
                PLAYWRIGHT_TEST,
                "--output",
                str(evidence_dir / "playwright-test-results"),
                "--trace",
                "retain-on-failure",
            ],
            cwd=frontend_dir,
            evidence_dir=evidence_dir,
            env=frontend_env,
        )

    if args.live_codex:
        _run_live_codex_check(evidence_dir)

    print(f"Codex-first validation passed. Evidence: {evidence_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
