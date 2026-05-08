from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def has_commit() -> bool:
    result = run_git("rev-parse", "--verify", "HEAD", check=False)
    return result.returncode == 0


def main() -> None:
    if not (ROOT / ".git").exists():
        run_git("init")
        run_git("checkout", "-B", "main")

    if has_commit():
        print(f"Fixture repository is ready: {ROOT}")
        return

    run_git("add", ".")
    run_git(
        "-c",
        "user.email=fixture@example.com",
        "-c",
        "user.name=context-eval fixture",
        "commit",
        "-m",
        "Initial fixture repo",
    )
    print(f"Fixture repository initialized: {ROOT}")


if __name__ == "__main__":
    main()
