from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from context_eval.models import CommandResult


def run_command(
    command: str | Sequence[str],
    cwd: Path,
    timeout_seconds: int | None = None,
    shell: bool | None = None,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a command and capture enough metadata for evaluation artifacts."""
    started = time.monotonic()
    use_shell = isinstance(command, str) if shell is None else shell
    command_text = command if isinstance(command, str) else " ".join(command)
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            shell=use_shell,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env={**os.environ, **env} if env else None,
        )
        return CommandResult(
            command=command_text,
            cwd=str(cwd),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=time.monotonic() - started,
            timeout=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout
            if isinstance(exc.stdout, str)
            else (exc.stdout or b"").decode(errors="replace")
        )
        stderr = (
            exc.stderr
            if isinstance(exc.stderr, str)
            else (exc.stderr or b"").decode(errors="replace")
        )
        return CommandResult(
            command=command_text,
            cwd=str(cwd),
            exit_code=None,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=time.monotonic() - started,
            timeout=True,
        )
