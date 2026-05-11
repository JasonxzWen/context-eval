import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


def _write_wheel(path: Path, entries: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for entry in entries:
            archive.writestr(entry, "")


def _write_sdist(path: Path, entries: list[str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for entry in entries:
            data = b""
            info = tarfile.TarInfo(entry)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def _write_valid_artifacts(dist_dir: Path) -> None:
    _write_wheel(
        dist_dir / "context_eval-0.1.0-py3-none-any.whl",
        [
            "context_eval/__init__.py",
            "context_eval/reports/templates/report.md.j2",
            "context_eval-0.1.0.dist-info/METADATA",
        ],
    )
    _write_sdist(
        dist_dir / "context_eval-0.1.0.tar.gz",
        [
            "context_eval-0.1.0/pyproject.toml",
            "context_eval-0.1.0/context_eval/__init__.py",
            "context_eval-0.1.0/context_eval/reports/templates/report.md.j2",
        ],
    )


def _run_inspector(dist_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/inspect-package-artifacts.py", str(dist_dir)],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )


def test_package_artifact_inspector_accepts_runtime_only_wheel_and_sdist(
    tmp_path: Path,
) -> None:
    _write_valid_artifacts(tmp_path)

    result = _run_inspector(tmp_path)

    assert result.returncode == 0
    assert "Package artifact inspection passed" in result.stdout


def test_package_artifact_inspector_rejects_missing_runtime_entries(tmp_path: Path) -> None:
    _write_wheel(
        tmp_path / "context_eval-0.1.0-py3-none-any.whl",
        ["context_eval/__init__.py"],
    )
    _write_sdist(
        tmp_path / "context_eval-0.1.0.tar.gz",
        ["context_eval-0.1.0/context_eval/__init__.py"],
    )

    result = _run_inspector(tmp_path)

    assert result.returncode == 1
    assert "missing required entry" in result.stderr
    assert "context_eval/reports/templates/" in result.stderr


def test_package_artifact_inspector_rejects_forbidden_entries(tmp_path: Path) -> None:
    _write_wheel(
        tmp_path / "context_eval-0.1.0-py3-none-any.whl",
        [
            "context_eval/__init__.py",
            "context_eval/reports/templates/report.md.j2",
            ".agents/skills/example/SKILL.md",
        ],
    )
    _write_sdist(
        tmp_path / "context_eval-0.1.0.tar.gz",
        [
            "context_eval-0.1.0/context_eval/__init__.py",
            "context_eval-0.1.0/context_eval/reports/templates/report.md.j2",
            "context_eval-0.1.0/scripts/validate-skills.ps1",
        ],
    )

    result = _run_inspector(tmp_path)

    assert result.returncode == 1
    assert "forbidden entry" in result.stderr
    assert ".agents/" in result.stderr
    assert "scripts/" in result.stderr
