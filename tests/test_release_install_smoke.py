import subprocess
import sys
from pathlib import Path


def _run_install_smoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/install-smoke-artifacts.py", *args],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )


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
    assert "examples/fixture-repo" in result.stdout.replace("\\", "/")
    assert "hosted service" not in result.stdout.lower()
    assert "http://" not in result.stdout
    assert "https://" not in result.stdout
