from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import yaml

from context_eval.config import ConfigError

GENERIC_AGENT_COMMAND = "agent -p {prompt_file}"
CODEX_EXEC_JSON_COMMAND = (
    'codex exec --json --sandbox workspace-write '
    '--output-last-message "{output_dir}/codex-final-message.md" '
    '-C "{workspace}" - < "{prompt_file}"'
)
COCO_UNATTENDED_COMMAND = (
    'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"'
)


def create_starter_files(
    *,
    directory: Path,
    repo_path: str,
    agent_command: str,
    agent_profiles: bool = False,
    force: bool = False,
) -> list[Path]:
    targets = {
        directory / "context-eval.yaml": _config_yaml(
            repo_path,
            agent_command,
            agent_profiles=agent_profiles,
        ),
        directory / "tasks.yaml": _tasks_yaml(),
        directory / "contexts" / "baseline" / "AGENTS.md": _baseline_agents(),
        directory / "contexts" / "experiment" / "AGENTS.md": _experiment_agents(),
    }

    existing = [path for path in targets if path.exists()]
    if existing and not force:
        formatted = ", ".join(str(path) for path in existing)
        raise ConfigError(f"starter file already exists: {formatted}")

    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return list(targets)


def _agent_profile(
    kind: str,
    command: str,
    *,
    telemetry: dict[str, object] | None = None,
) -> dict[str, object]:
    profile: dict[str, object] = {
        "kind": kind,
        "command": command,
        "timeout_minutes": 60,
        "network": "disabled",
    }
    if telemetry is not None:
        profile["telemetry"] = telemetry
    return profile


def _config_yaml(repo_path: str, agent_command: str, *, agent_profiles: bool) -> str:
    agent_section: dict[str, object]
    if agent_profiles:
        coco_command = (
            COCO_UNATTENDED_COMMAND
            if agent_command == GENERIC_AGENT_COMMAND
            else agent_command
        )
        agent_section = {
            "agents": {
                "codex": _agent_profile(
                    "codex-cli",
                    CODEX_EXEC_JSON_COMMAND,
                    telemetry={
                        "collector": "codex-jsonl",
                        "file": "codex-events.jsonl",
                    },
                ),
                "claude": _agent_profile("claude-code", "claude -p {prompt_file}"),
                "trae": _agent_profile("traecli", 'traecli -p "{prompt}"'),
                "coco": _agent_profile("coco", coco_command),
            }
        }
    else:
        agent_section = {
            "agent": {
                "name": "local-agent",
                "command": agent_command,
                "timeout_minutes": 60,
                "network": "disabled",
            }
        }

    return yaml.safe_dump(
        {
            "repo": {
                "path": repo_path,
                "base_ref": "HEAD",
            },
            **agent_section,
            "tasks": "./tasks.yaml",
            "variants": {
                "baseline": {
                    "description": "Baseline instructions",
                    "overlays": [
                        {
                            "source": "./contexts/baseline/AGENTS.md",
                            "target": "AGENTS.md",
                        }
                    ],
                },
                "experiment": {
                    "description": "Experiment instructions",
                    "overlays": [
                        {
                            "source": "./contexts/experiment/AGENTS.md",
                            "target": "AGENTS.md",
                        }
                    ],
                },
            },
            "evaluation": {"commands": []},
        },
        sort_keys=False,
    )


def _tasks_yaml() -> str:
    return dedent(
        """\
        tasks:
          - id: "sample-task"
            title: "Make a focused sample change"
            prompt: |
              Make the smallest useful change for this repository.
              Follow the active instructions and do not commit changes.
            category: "sample"
            difficulty: "easy"
        """
    )


def _baseline_agents() -> str:
    return dedent(
        """\
        # Agent Instructions

        Follow the existing repository conventions. Keep changes focused and minimal.
        """
    )


def _experiment_agents() -> str:
    return dedent(
        """\
        # Agent Instructions

        Follow the existing repository conventions. Prefer small, reviewable patches.
        Before editing, inspect nearby files and relevant project documentation.
        Do not commit changes.
        """
    )
