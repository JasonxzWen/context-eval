from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from context_eval.config import ConfigError, filter_tasks, validate_config_files
from context_eval.dry_run import render_dry_run
from context_eval.init import create_starter_files
from context_eval.reports.markdown import render_markdown_report
from context_eval.runner import ContextEvalRunner

app = typer.Typer(help="Context A/B testing framework for coding agents.")
console = Console()


@app.command("init")
def init_command(
    directory: Annotated[
        Path,
        typer.Option("--directory", "-d", file_okay=False, help="Directory to initialize."),
    ] = Path("."),
    repo_path: Annotated[
        str,
        typer.Option("--repo-path", help="Repo path to write into context-eval.yaml."),
    ] = ".",
    agent_command: Annotated[
        str,
        typer.Option("--agent-command", help="Agent command template to write."),
    ] = "agent -p {prompt_file}",
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite starter files if they already exist."),
    ] = False,
) -> None:
    """Generate starter config, tasks, and context files."""
    try:
        created = create_starter_files(
            directory=directory,
            repo_path=repo_path,
            agent_command=agent_command,
            force=force,
        )
    except ConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Initialized context-eval files in:[/green] {directory.resolve()}")
    for path in created:
        console.print(f"- {path}")


@app.command()
def run(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, dir_okay=False)],
    tasks: Annotated[Path | None, typer.Option("--tasks", dir_okay=False)] = None,
    cleanup: Annotated[
        bool,
        typer.Option("--cleanup", help="Delete workspaces after each case."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview selected cases without creating run artifacts."),
    ] = False,
    max_tasks: Annotated[int | None, typer.Option("--max-tasks", min=1)] = None,
    variant: Annotated[
        list[str] | None,
        typer.Option("--variant", help="Variant to run. Repeatable."),
    ] = None,
    task_id: Annotated[
        list[str] | None,
        typer.Option("--task-id", help="Task ID to run. Repeatable."),
    ] = None,
    category: Annotated[
        list[str] | None,
        typer.Option("--category", help="Task category to run. Repeatable."),
    ] = None,
    difficulty: Annotated[
        list[str] | None,
        typer.Option("--difficulty", help="Task difficulty to run. Repeatable."),
    ] = None,
) -> None:
    """Run tasks across context variants."""
    try:
        loaded_config, task_file = validate_config_files(config, tasks)
        task_file = filter_tasks(
            task_file,
            task_ids=task_id,
            categories=category,
            difficulties=difficulty,
        )
        if dry_run:
            render_dry_run(
                config=loaded_config,
                tasks=task_file,
                variants=variant,
                max_tasks=max_tasks,
                console=console,
            )
            return
        runner = ContextEvalRunner(
            config=loaded_config,
            tasks=task_file,
            cleanup=cleanup,
            max_tasks=max_tasks,
            variants=variant,
            console=console,
        )
        run_dir = runner.run()
    except (ConfigError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Run complete:[/green] {run_dir}")
    console.print(f"Report: {run_dir / 'report.md'}")


@app.command("report")
def report_command(run_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """Regenerate a Markdown report for a run directory."""
    try:
        report_path = render_markdown_report(run_dir)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Report written:[/green] {report_path}")


@app.command("validate-config")
def validate_config(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, dir_okay=False)],
    tasks: Annotated[Path | None, typer.Option("--tasks", dir_okay=False)] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Verify local Git repo and refs without side effects."),
    ] = False,
) -> None:
    """Validate configuration and task YAML files."""
    try:
        loaded_config, task_file = validate_config_files(config, tasks, strict=strict)
    except ConfigError as exc:
        console.print(f"[red]Invalid config:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[green]Config valid[/green]")
    console.print(f"Repo: {loaded_config.repo.path}")
    console.print(f"Tasks: {len(task_file.tasks)}")
    console.print(f"Variants: {', '.join(loaded_config.variants.keys())}")


if __name__ == "__main__":
    app()
