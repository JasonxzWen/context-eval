from __future__ import annotations

from pathlib import Path

from context_eval.logging import run_command
from context_eval.models import CommandResult


def run_validation_commands(commands: list[str], workspace: Path) -> list[CommandResult]:
    return [run_command(command, cwd=workspace, shell=True) for command in commands]
