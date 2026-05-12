from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from context_eval.compare import compare_run
from context_eval.config import ConfigError, filter_tasks, validate_config_files
from context_eval.dry_run import render_dry_run
from context_eval.export import export_run_csv, export_run_json
from context_eval.init import create_starter_files
from context_eval.inspect_run import inspect_run
from context_eval.reports.markdown import render_markdown_report
from context_eval.runner import ContextEvalRunner
from context_eval.ui import render_local_ui

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
    agent_profiles: Annotated[
        bool,
        typer.Option(
            "--agent-profiles",
            help="Write a named agents profile map instead of a legacy single agent.",
        ),
    ] = False,
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
            agent_profiles=agent_profiles,
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
    cleanup_policy: Annotated[
        str | None,
        typer.Option(
            "--cleanup-policy",
            help="Workspace cleanup policy: never, always, successful, or failed.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview selected cases without creating run artifacts."),
    ] = False,
    max_tasks: Annotated[int | None, typer.Option("--max-tasks", min=1)] = None,
    trials: Annotated[int, typer.Option("--trials", min=1, help="Trials per task/variant.")] = 1,
    jobs: Annotated[
        int,
        typer.Option("--jobs", min=1, help="Maximum concurrent cases."),
    ] = 1,
    variant: Annotated[
        list[str] | None,
        typer.Option("--variant", help="Variant to run. Repeatable."),
    ] = None,
    agent: Annotated[
        list[str] | None,
        typer.Option("--agent", help="Agent profile to run. Repeatable."),
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
        resolved_cleanup_policy = ContextEvalRunner.resolve_cleanup_policy(
            cleanup=cleanup,
            cleanup_policy=cleanup_policy,
        )
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
                agents=agent,
                max_tasks=max_tasks,
                trials=trials,
                jobs=jobs,
                cleanup_policy=resolved_cleanup_policy,
                console=console,
            )
            return
        runner = ContextEvalRunner(
            config=loaded_config,
            tasks=task_file,
            cleanup_policy=resolved_cleanup_policy,
            max_tasks=max_tasks,
            agents=agent,
            variants=variant,
            trials=trials,
            jobs=jobs,
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


@app.command("inspect-run")
def inspect_run_command(
    run_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
) -> None:
    """Print a terminal summary for an existing run directory."""
    try:
        inspect_run(run_dir, console)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("compare")
def compare_command(
    run_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
) -> None:
    """Compare variant metrics for an existing run directory."""
    try:
        compare_run(run_dir, console)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("export")
def export_command(
    run_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    export_format: Annotated[
        str,
        typer.Option("--format", help="Export format: csv or json."),
    ] = "csv",
    output: Annotated[
        Path,
        typer.Option("--output", "-o", dir_okay=False, help="Output file to write."),
    ] = Path("context-eval-summary.csv"),
) -> None:
    """Export deterministic run summaries from an existing run directory."""
    try:
        if export_format == "csv":
            content = export_run_csv(run_dir)
        elif export_format == "json":
            content = export_run_json(run_dir)
        else:
            raise ValueError(f"unsupported export format: {export_format}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Export written:[/green] {output}")


@app.command("ui")
def ui_command(
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", exists=True, dir_okay=False),
    ] = None,
    run_dir: Annotated[
        Path | None,
        typer.Option("--run-dir", exists=True, file_okay=False),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", dir_okay=False, help="HTML file to write."),
    ] = Path("context-eval-ui.html"),
) -> None:
    """Generate a self-contained local HTML interface."""
    try:
        output_path = render_local_ui(config_path=config, run_dir=run_dir, output_path=output)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]UI written:[/green] {output_path}")


@app.command("validate-config")
def validate_config(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, dir_okay=False)],
    tasks: Annotated[Path | None, typer.Option("--tasks", dir_okay=False)] = None,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Verify local Git refs and filename-safe task IDs without side effects.",
        ),
    ] = False,
    check_agents: Annotated[
        bool,
        typer.Option(
            "--check-agents",
            help="Verify agent command executables are available without running them.",
        ),
    ] = False,
) -> None:
    """Validate configuration and task YAML files."""
    try:
        loaded_config, task_file = validate_config_files(
            config,
            tasks,
            strict=strict,
            check_agents=check_agents,
        )
    except ConfigError as exc:
        console.print(f"[red]Invalid config:[/red] {exc}", soft_wrap=True)
        raise typer.Exit(code=1) from exc

    console.print("[green]Config valid[/green]")
    console.print(f"Repo: {loaded_config.repo.path}")
    console.print(f"Agents: {', '.join(loaded_config.agent_profiles().keys())}")
    console.print(f"Tasks: {len(task_file.tasks)}")
    console.print(f"Variants: {', '.join(loaded_config.variants.keys())}")
    if check_agents:
        console.print("Agent executables: checked")


if __name__ == "__main__":
    app()
