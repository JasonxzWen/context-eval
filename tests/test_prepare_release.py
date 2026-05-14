import subprocess
import sys
from pathlib import Path


def _run_prepare_release(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/prepare-release.py", *args],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )


def _write_minimal_release_root(root: Path) -> None:
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n- Prepare release automation.\n",
        encoding="utf-8",
    )


def test_prepare_release_dry_run_checks_changelog_and_prints_plan(tmp_path: Path) -> None:
    _write_minimal_release_root(tmp_path)
    dist_dir = tmp_path / "release-dist"

    result = _run_prepare_release("--root", str(tmp_path), "--dist-dir", str(dist_dir), "--dry-run")

    assert result.returncode == 0
    assert "CHANGELOG.md check passed" in result.stdout
    assert "Release state check passed" in result.stdout
    assert "DRY RUN: would run" in result.stdout
    assert "python -m build --outdir" in result.stdout
    assert "python scripts/inspect-package-artifacts.py" in result.stdout
    assert "python scripts/install-smoke-artifacts.py" in result.stdout
    assert "Manual publish checkpoint: create tags and upload packages outside this script." in (
        result.stdout
    )


def test_prepare_release_accepts_empty_unreleased_with_release_notes(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n## v0.1.2 - 2026-05-14\n\n- Release notes.\n",
        encoding="utf-8",
    )
    dist_dir = tmp_path / "release-dist"

    result = _run_prepare_release("--root", str(tmp_path), "--dist-dir", str(dist_dir), "--dry-run")

    assert result.returncode == 0
    assert "CHANGELOG.md check passed" in result.stdout


def test_prepare_release_rejects_missing_unreleased_changelog(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\n", encoding="utf-8")

    result = _run_prepare_release(
        "--root",
        str(tmp_path),
        "--dist-dir",
        str(tmp_path / "release-dist"),
        "--dry-run",
    )

    assert result.returncode == 1
    assert "CHANGELOG.md must contain ## Unreleased" in result.stderr


def test_prepare_release_rejects_hidden_release_blockers(tmp_path: Path) -> None:
    _write_minimal_release_root(tmp_path)
    (tmp_path / ".context-eval").mkdir()

    result = _run_prepare_release(
        "--root",
        str(tmp_path),
        "--dist-dir",
        str(tmp_path / "release-dist"),
        "--dry-run",
    )

    assert result.returncode == 1
    assert "hidden local release blocker: .context-eval/" in result.stderr


def test_prepare_release_rejects_existing_dist_artifacts(tmp_path: Path) -> None:
    _write_minimal_release_root(tmp_path)
    dist_dir = tmp_path / "release-dist"
    dist_dir.mkdir()
    (dist_dir / "old.whl").write_text("", encoding="utf-8")

    result = _run_prepare_release("--root", str(tmp_path), "--dist-dir", str(dist_dir), "--dry-run")

    assert result.returncode == 1
    assert "dist directory must be empty before release build" in result.stderr
