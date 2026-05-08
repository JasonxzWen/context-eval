from __future__ import annotations

from pathlib import Path

from context_eval.models import TaskConfig


def render_prompt(task: TaskConfig, variant: str) -> str:
    title = task.title or task.id
    return "\n".join(
        [
            "# Coding Agent Task",
            "",
            f"Task ID: {task.id}",
            f"Task Title: {title}",
            f"Context Variant: {variant}",
            "",
            "## User Task",
            "",
            task.prompt.strip(),
            "",
            "## Instructions",
            "",
            "- Modify files in the repository as needed.",
            "- Do not commit changes.",
            "- Keep changes minimal.",
            "- Run relevant checks if available.",
            "- Leave the workspace with your final code changes.",
            "",
        ]
    )


def write_prompt_file(path: Path, task: TaskConfig, variant: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_prompt(task, variant), encoding="utf-8")
    return path
