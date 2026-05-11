import subprocess
import sys
from pathlib import Path


def _run_release_state_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/check-release-state.py", str(root)],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )


def test_release_state_check_allows_clean_dev_cache_and_ralph_state(tmp_path: Path) -> None:
    for path in [
        ".venv",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "scripts/ralph",
    ]:
        (tmp_path / path).mkdir(parents=True)

    for path in [
        "scripts/ralph/prd.json",
        "scripts/ralph/progress.txt",
        "scripts/ralph/.last-branch",
    ]:
        (tmp_path / path).write_text("", encoding="utf-8")

    result = _run_release_state_check(tmp_path)

    assert result.returncode == 0
    assert "Release state check passed" in result.stdout


def test_release_state_check_rejects_hidden_release_blockers(tmp_path: Path) -> None:
    for path in [".context-eval", "build", "dist", "context_eval.egg-info"]:
        (tmp_path / path).mkdir()

    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex/config.toml").write_text("", encoding="utf-8")

    result = _run_release_state_check(tmp_path)

    assert result.returncode == 1
    assert ".context-eval/" in result.stderr
    assert "build/" in result.stderr
    assert "dist/" in result.stderr
    assert "context_eval.egg-info/" in result.stderr
    assert ".codex/config.toml" in result.stderr
