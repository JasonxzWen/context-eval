from __future__ import annotations

from rich.console import Console

from context_eval.models import AgentConfig, ContextEvalConfig, TaskConfig, TaskFile
from context_eval.workspace import slugify


def render_dry_run(
    *,
    config: ContextEvalConfig,
    tasks: TaskFile,
    variants: list[str] | None = None,
    agents: list[str] | None = None,
    max_tasks: int | None = None,
    trials: int = 1,
    jobs: int = 1,
    cleanup_policy: str = "never",
    console: Console,
) -> None:
    selected_tasks = tasks.tasks[:max_tasks] if max_tasks else tasks.tasks
    agent_profiles = _agent_profiles(config, agents or [])
    variant_names = _variant_names(config, variants or [])

    console.print("[bold]Dry run[/bold] - no workspaces, agents, patches, or results created")
    console.print(f"Repo: {config.repo.path}")
    console.print(f"Output dir: {config.output_dir}")
    console.print(f"Agents: {', '.join(profile.name for profile in agent_profiles)}")
    console.print(f"Tasks: {', '.join(task.id for task in selected_tasks)}")
    console.print(f"Variants: {', '.join(variant_names)}")
    console.print(f"Trials: {trials}")
    console.print(f"Jobs: {jobs}")
    console.print(f"Cleanup policy: {cleanup_policy}")
    console.print("")
    console.print("[bold]Agent x Task x Variant Matrix[/bold]")

    for agent_profile in agent_profiles:
        for task in selected_tasks:
            for variant_name in variant_names:
                for trial_index in range(1, trials + 1):
                    _print_case(
                        console=console,
                        config=config,
                        agent_profile=agent_profile,
                        task=task,
                        variant_name=variant_name,
                        trial_index=trial_index,
                        trials=trials,
                    )


def _print_case(
    *,
    console: Console,
    config: ContextEvalConfig,
    agent_profile: AgentConfig,
    task: TaskConfig,
    variant_name: str,
    trial_index: int,
    trials: int,
) -> None:
    repo_ref = task.repo_ref or config.repo.base_ref
    case_name = _case_id(
        task.id,
        variant_name,
        trial_index,
        trials,
        agent_name=agent_profile.name if config.uses_agent_profile_map() else None,
    )
    commands = task.validation.commands or config.evaluation.commands
    timeout_seconds = (
        task.validation.timeout_seconds
        if task.validation.timeout_seconds is not None
        else config.evaluation.timeout_seconds
    )
    console.print(
        f"- agent={agent_profile.name} task={task.id} variant={variant_name} "
        f"trial={trial_index} repo_ref={repo_ref}"
    )
    console.print(f"  case_id={case_name}")
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
        if timeout_seconds is not None:
            console.print(f"    timeout_seconds={timeout_seconds}")
        for command in commands:
            console.print(f"    - {command}")
    else:
        console.print("    - none")


def _agent_profiles(config: ContextEvalConfig, selected_agents: list[str]) -> list[AgentConfig]:
    profiles = config.agent_profiles()
    if not selected_agents:
        return list(profiles.values())
    unknown = [name for name in selected_agents if name not in profiles]
    if unknown:
        raise ValueError(f"unknown agent profile(s): {', '.join(unknown)}")
    return [profiles[name] for name in selected_agents]


def _variant_names(config: ContextEvalConfig, selected_variants: list[str]) -> list[str]:
    if not selected_variants:
        return list(config.variants.keys())
    unknown = [name for name in selected_variants if name not in config.variants]
    if unknown:
        raise ValueError(f"unknown variant(s): {', '.join(unknown)}")
    return selected_variants


def _case_id(
    task_id: str,
    variant_name: str,
    trial_index: int,
    trials: int,
    *,
    agent_name: str | None = None,
) -> str:
    base = f"{slugify(task_id)}__{slugify(variant_name)}"
    if agent_name:
        base = f"{base}__{slugify(agent_name)}"
    if trials == 1:
        return base
    return f"{base}__trial-{trial_index}"
