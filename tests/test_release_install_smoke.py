import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _run_install_smoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/install-smoke-artifacts.py", *args],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )


def _load_install_smoke_module() -> ModuleType:
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "install-smoke-artifacts.py"
    spec = importlib.util.spec_from_file_location("install_smoke_artifacts", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_install_smoke_rejects_missing_wheel(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()

    result = _run_install_smoke("--dist-dir", str(dist_dir), "--dry-run")

    assert result.returncode == 1
    assert "missing wheel artifact" in result.stderr


def test_release_install_smoke_dry_run_uses_local_wheel_and_fixture_only(
    tmp_path: Path,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "context_eval-0.1.0-py3-none-any.whl").write_bytes(b"placeholder")

    result = _run_install_smoke("--dist-dir", str(dist_dir), "--dry-run")

    assert result.returncode == 0
    assert "DRY RUN: would create temporary Python environment" in result.stdout
    assert "python -m pip install --no-deps --force-reinstall" in result.stdout
    assert "context-eval validate-config" in result.stdout
    assert "context-eval run" in result.stdout
    assert "context-eval report" in result.stdout
    assert "context-eval export" in result.stdout
    assert "context-eval ui" in result.stdout
    assert "context-eval-app --workspace <temp>" in result.stdout
    assert "--no-browser --port 0 --check-startup" in result.stdout
    assert "examples/fixture-repo" in result.stdout.replace("\\", "/")
    assert "hosted service" not in result.stdout.lower()
    assert "http://" not in result.stdout
    assert "https://" not in result.stdout


def test_release_install_smoke_runs_installed_launcher_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_install_smoke_module()
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "context_eval-0.1.0-py3-none-any.whl").write_bytes(b"placeholder")
    work_dir = tmp_path / "work"
    commands: list[list[str]] = []

    class _FakeEnvBuilder:
        def __init__(self, **_: object) -> None:
            pass

        def create(self, venv_dir: Path) -> None:
            script_dir = venv_dir / ("Scripts" if sys.platform == "win32" else "bin")
            script_dir.mkdir(parents=True)

    def fake_run(command: list[str], *, cwd: Path, timeout_seconds: int = 180) -> int:
        commands.append(command)
        if "run" in command:
            (work_dir / "runs" / "run-1").mkdir(parents=True, exist_ok=True)
        return 0

    monkeypatch.setattr(module.venv, "EnvBuilder", _FakeEnvBuilder)
    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "_validate_artifacts", lambda *_: [])

    result = module.run_install_smoke(
        root=Path(__file__).resolve().parents[1],
        dist_dir=dist_dir,
        work_dir=work_dir,
        dry_run=False,
    )

    assert result == 0
    launcher_commands = [
        command for command in commands if Path(command[0]).name.startswith("context-eval-app")
    ]
    assert launcher_commands == [
        [
            str(module._launcher_script(work_dir / "venv")),
            "--workspace",
            str(work_dir),
            "--config",
            str(work_dir / "context-eval.yaml"),
            "--no-browser",
            "--port",
            "0",
            "--check-startup",
        ]
    ]
