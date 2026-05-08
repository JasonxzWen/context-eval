from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from context_eval.config import ConfigError, load_config, validate_config_files
from context_eval.reports.markdown import render_markdown_report
from context_eval.runner import ContextEvalRunner

app = typer.Typer(help="Context A/B testing framework for coding agents.")
console = Console()


@app.command()
def run(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, dir_okay=False)],
    tasks: Annotated[Path | None, typer.Option("--tasks", dir_okay=False)] = None,
    cleanup: Annotated[
        bool,
        typer.Option("--cleanup", help="Delete workspaces after each case."),
    ] = False,
    max_tasks: Annotated[int | None, typer.Option("--max-tasks", min=1)] = None,
    variant: Annotated[
        list[str] | None,
        typer.Option("--variant", help="Variant to run. Repeatable."),
    ] = None,
) -> None:
    """Run tasks across context variants."""
    try:
        loaded_config, task_file = validate_config_files(config, tasks)
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
