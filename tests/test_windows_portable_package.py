from __future__ import annotations

import subprocess
import sys
import zipfile
from importlib import util
from pathlib import Path
from types import ModuleType

import pytest


def _run_builder(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/build-windows-portable.py", *args],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )


def _load_builder_module() -> ModuleType:
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "build-windows-portable.py"
    spec = util.spec_from_file_location("build_windows_portable", path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_windows_portable_builder_requires_context_eval_wheel(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    frontend_dist = tmp_path / "frontend-dist"
    output_dir = tmp_path / "out"
    dist_dir.mkdir()
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<main>context-eval</main>", encoding="utf-8")

    result = _run_builder(
        "--dist-dir",
        str(dist_dir),
        "--frontend-dist",
        str(frontend_dist),
        "--output-dir",
        str(output_dir),
        "--skip-dependency-download",
    )

    assert result.returncode == 1
    assert "missing wheel artifact" in result.stderr


def test_windows_portable_builder_creates_double_click_zip(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    frontend_dist = tmp_path / "frontend-dist"
    output_dir = tmp_path / "out"
    dist_dir.mkdir()
    frontend_dist.mkdir()
    output_dir.mkdir()
    (dist_dir / "context_eval-0.1.1-py3-none-any.whl").write_bytes(b"placeholder")
    (frontend_dist / "index.html").write_text("<main>context-eval</main>", encoding="utf-8")
    (frontend_dist / "assets").mkdir()
    (frontend_dist / "assets" / "app.js").write_text("console.log('ok')\n", encoding="utf-8")

    result = _run_builder(
        "--dist-dir",
        str(dist_dir),
        "--frontend-dist",
        str(frontend_dist),
        "--output-dir",
        str(output_dir),
        "--skip-dependency-download",
    )

    assert result.returncode == 0, result.stderr
    archive = output_dir / "context-eval-windows-x64-0.1.1.zip"
    assert archive.exists()

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        root = "context-eval-windows-x64-0.1.1/"
        for expected in [
            f"{root}Start Context Eval.cmd",
            f"{root}README.txt",
            f"{root}scripts/start-context-eval.ps1",
            f"{root}wheelhouse/context_eval-0.1.1-py3-none-any.whl",
            f"{root}frontend/dist/index.html",
            f"{root}frontend/dist/assets/app.js",
        ]:
            assert expected in names

        cmd_text = package.read(f"{root}Start Context Eval.cmd").decode("utf-8")
        ps1_text = package.read(f"{root}scripts/start-context-eval.ps1").decode("utf-8")
        readme_text = package.read(f"{root}README.txt").decode("utf-8")

    assert "powershell" in cmd_text
    assert "scripts\\start-context-eval.ps1" in cmd_text
    for term in [
        "Python 3.11",
        "--no-index",
        "--find-links",
        "--frontend-dist",
        "frontend\\dist",
        "context-eval-app",
        "workspace",
    ]:
        assert term in ps1_text
    for term in [
        "Double-click Start Context Eval.cmd",
        "Python 3.11 or newer is required",
        "does not install coding agents",
        "does not install target repository dependencies",
        "does not create Git tags",
        "does not publish packages",
    ]:
        assert term in readme_text


def test_windows_portable_builder_downloads_supported_windows_python_wheels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_builder_module()
    dist_dir = tmp_path / "dist"
    frontend_dist = tmp_path / "frontend-dist"
    output_dir = tmp_path / "out"
    dist_dir.mkdir()
    frontend_dist.mkdir()
    (dist_dir / "context_eval-0.1.1-py3-none-any.whl").write_bytes(b"placeholder")
    (frontend_dist / "index.html").write_text("<main>context-eval</main>", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert check is True
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    archive = module.build_windows_portable(
        dist_dir=dist_dir,
        frontend_dist=frontend_dist,
        output_dir=output_dir,
        skip_dependency_download=False,
    )

    assert archive == output_dir / "context-eval-windows-x64-0.1.1.zip"
    versions = {
        command[command.index("--python-version") + 1]: command[command.index("--abi") + 1]
        for command in commands
    }
    assert versions == {"3.11": "cp311", "3.12": "cp312", "3.13": "cp313"}
    assert all("--platform" in command and "win_amd64" in command for command in commands)
