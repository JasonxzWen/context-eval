from __future__ import annotations

from pathlib import Path

from context_eval.models import TaskConfig


def render_prompt(
    task: TaskConfig,
    variant: str,
    *,
    prompt_template: Path | None = None,
    repo_ref: str | None = None,
) -> str:
    if prompt_template is not None:
        return render_prompt_template(prompt_template, task, variant, repo_ref=repo_ref)

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


def render_prompt_template(
    prompt_template: Path,
    task: TaskConfig,
    variant: str,
    *,
    repo_ref: str | None,
) -> str:
    template = prompt_template.read_text(encoding="utf-8")
    variables = {
        "task_id": task.id,
        "task_title": task.title or task.id,
        "task_prompt": task.prompt.strip(),
        "variant": variant,
        "repo_ref": repo_ref or task.repo_ref or "",
        "category": task.category or "",
        "difficulty": task.difficulty or "",
    }
    try:
        return template.format(**variables)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(f"prompt template references unknown variable: {missing}") from exc


def write_prompt_file(
    path: Path,
    task: TaskConfig,
    variant: str,
    *,
    prompt_template: Path | None = None,
    repo_ref: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_prompt(
            task,
            variant,
            prompt_template=prompt_template,
            repo_ref=repo_ref,
        ),
        encoding="utf-8",
    )
    return path
