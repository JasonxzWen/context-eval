from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from context_eval.models import CommandResult, TaskConfig


class AgentAdapter(ABC):
    @abstractmethod
    def run(
        self,
        *,
        workspace: Path,
        prompt: str,
        prompt_file: Path,
        task: TaskConfig,
        variant: str,
        output_dir: Path,
        timeout_seconds: int,
    ) -> CommandResult:
        """Run an agent against a prepared workspace."""
