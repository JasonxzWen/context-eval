from __future__ import annotations

from rich.console import Console

from context_eval.models import ContextEvalConfig, TaskFile
from context_eval.workspace import slugify


def render_dry_run(
    *,
    config: ContextEvalConfig,
    tasks: TaskFile,
    variants: list[str] | None = None,
    max_tasks: int | None = None,
    console: Console,
) -> None:
    selected_tasks = tasks.tasks[:max_tasks] if max_tasks else tasks.tasks
    variant_names = _variant_names(config, variants or [])

    console.print("[bold]Dry run[/bold] - no workspaces, agents, patches, or results created")
    console.print(f"Repo: {config.repo.path}")
    console.print(f"Output dir: {config.output_dir}")
    console.print(f"Tasks: {', '.join(task.id for task in selected_tasks)}")
    console.print(f"Variants: {', '.join(variant_names)}")
    console.print("")
    console.print("[bold]Task x Variant Matrix[/bold]")

    for task in selected_tasks:
        for variant_name in variant_names:
            repo_ref = task.repo_ref or config.repo.base_ref
            case_name = f"{slugify(task.id)}__{slugify(variant_name)}"
            commands = task.validation.commands or config.evaluation.commands
            console.print(f"- task={task.id} variant={variant_name} repo_ref={repo_ref}")
            console.print(f"  prompt=prompts/{case_name}.md")
            console.print("  overlays:")
            overlays = config.variants[variant_name].overlays
            if overlays:
                for overlay in overlays:
                    console.print(f"    - {overlay.source.name} -> {overlay.target}")
            else:
                console.print("    - none")
            console.print("  validation:")
            if commands:
                for command in commands:
                    console.print(f"    - {command}")
            else:
                console.print("    - none")


def _variant_names(config: ContextEvalConfig, selected_variants: list[str]) -> list[str]:
    if not selected_variants:
        return list(config.variants.keys())
    unknown = [name for name in selected_variants if name not in config.variants]
    if unknown:
        raise ValueError(f"unknown variant(s): {', '.join(unknown)}")
    return selected_variants
