import io
import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest
from rich.console import Console

from context_eval import __version__
from context_eval.models import (
    RESULT_SCHEMA_VERSION,
    AgentConfig,
    AgentProfileConfig,
    AgentTelemetryConfig,
    CaseResult,
    ContextEvalConfig,
    EvaluationConfig,
    OverlayConfig,
    RepoConfig,
    TaskConfig,
    TaskFile,
    ValidationConfig,
    VariantConfig,
)
from context_eval.runner import ContextEvalRunner


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _create_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _run_git(repo, "add", "README.md")
    _run_git(
        repo,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test",
        "commit",
        "-m",
        "init",
    )
    return repo


def _quiet_console() -> Console:
    return Console(file=io.StringIO(), force_terminal=False)


def _base_config(
    *,
    tmp_path: Path,
    repo: Path,
    agent_command: str,
    overlay_source: Path,
    validation_commands: list[str] | None = None,
) -> ContextEvalConfig:
    return ContextEvalConfig(
        repo=RepoConfig(path=repo, base_ref="HEAD"),
        agent=AgentConfig(name="test-agent", command=agent_command, timeout_minutes=1),
        variants={
            "baseline": VariantConfig(
                description="Baseline",
                overlays=[OverlayConfig(source=overlay_source, target="AGENTS.md")],
            )
        },
        output_dir=tmp_path / "runs",
        evaluation=EvaluationConfig(commands=validation_commands or []),
    )


def test_runner_creates_versioned_result_report_and_agent_patch(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "from pathlib import Path\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'agent line\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    validation_script = tmp_path / "validate.py"
    validation_script.write_text(
        "from pathlib import Path\n"
        "readme = Path('README.md').read_text(encoding='utf-8')\n"
        "raise SystemExit(0 if 'agent line' in readme else 1)\n",
        encoding="utf-8",
    )

    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="smoke",
                prompt="Append a line.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{validation_script}"']),
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["schema_version"] == RESULT_SCHEMA_VERSION
    assert result["context_eval_version"] == __version__
    assert len(result["config_hash"]) == 16
    assert len(result["task_hash"]) == 16
    assert len(result["variant_hash"]) == 16
    assert result["status"] == "completed"
    assert result["validation_status"] == "passed"
    assert result["confidence"] == "high"
    assert result["telemetry_status"] == "unavailable"
    assert result["telemetry_source"] == "none"
    assert result["telemetry_error"] is None
    assert result["agent_duration_seconds"] >= 0
    assert result["prompt_tokens"] is None
    assert result["completion_tokens"] is None
    assert result["total_tokens"] is None
    assert result["reasoning_tokens"] is None
    assert result["tool_call_count"] is None
    assert result["tool_calls_by_name"] == {}
    assert result["changed_files"] == 1
    assert result["touched_paths"] == ["README.md"]
    assert result["workspace_retained"] is False
    assert result["cleanup_status"] == "succeeded"
    assert not (run_dir / result["workspace_path"]).exists()

    patch = (run_dir / result["patch_path"]).read_text(encoding="utf-8")
    assert "AGENTS.md" not in patch
    assert "+agent line" in patch

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "context-eval evaluates the effect of context variants" in report
    assert result["config_hash"] in report


def test_runner_records_json_file_agent_telemetry(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        "telemetry = Path(sys.argv[1])\n"
        "telemetry.parent.mkdir(parents=True, exist_ok=True)\n"
        "telemetry.write_text(json.dumps({\n"
        "    'prompt_tokens': 11,\n"
        "    'completion_tokens': 13,\n"
        "    'total_tokens': 24,\n"
        "    'reasoning_tokens': 3,\n"
        "    'tool_calls_by_name': {'read': 1, 'edit': 2},\n"
        "}), encoding='utf-8')\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'telemetry run\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    task_file = TaskFile(tasks=[TaskConfig(id="telemetry", prompt="Append a line.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}" "{{telemetry_file}}"',
        overlay_source=overlay_source,
    )
    config.agent.telemetry = AgentTelemetryConfig(collector="json-file")

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert result["telemetry_status"] == "collected"
    assert result["telemetry_source"] == "json-file"
    assert result["telemetry_error"] is None
    assert result["prompt_tokens"] == 11
    assert result["completion_tokens"] == 13
    assert result["total_tokens"] == 24
    assert result["reasoning_tokens"] == 3
    assert result["tool_call_count"] == 3
    assert result["tool_calls_by_name"] == {"read": 1, "edit": 2}
    assert metadata["agent"]["telemetry"] == {
        "collector": "json-file",
        "file": "telemetry.json",
        "environment_variable": "CONTEXT_EVAL_TELEMETRY_FILE",
    }


def test_runner_records_coco_structured_telemetry_reasoning_steps(
    tmp_path: Path,
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        "telemetry = Path(sys.argv[1])\n"
        "telemetry.parent.mkdir(parents=True, exist_ok=True)\n"
        "telemetry.write_text(json.dumps({\n"
        "    'agent_duration_seconds': 123.4,\n"
        "    'prompt_tokens': 10000,\n"
        "    'completion_tokens': 2000,\n"
        "    'reasoning_tokens': 3000,\n"
        "    'tool_call_count': 18,\n"
        "    'tool_calls_by_name': {'read_file': 6, 'edit_file': 3},\n"
        "    'reasoning_step_count': 12,\n"
        "}), encoding='utf-8')\n"
        "Path('README.md').write_text('base\\ntelemetry\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    task_file = TaskFile(tasks=[TaskConfig(id="coco-telemetry", prompt="Append a line.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}" "{{telemetry_file}}"',
        overlay_source=overlay_source,
    )
    config.agent.kind = "coco"
    config.agent.telemetry = AgentTelemetryConfig(collector="json-file")

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["telemetry_status"] == "collected"
    assert result["agent_duration_seconds"] == 123.4
    assert result["prompt_tokens"] == 10000
    assert result["completion_tokens"] == 2000
    assert result["reasoning_tokens"] == 3000
    assert result["tool_call_count"] == 18
    assert result["tool_calls_by_name"] == {"read_file": 6, "edit_file": 3}
    assert result["reasoning_step_count"] == 12


def test_runner_writes_hard_and_soft_evaluation_sidecars(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "from pathlib import Path\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'fixed marker\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    task_file = TaskFile.model_validate(
        {
            "tasks": [
                {
                    "id": "hybrid-pass",
                    "prompt": "Add fixed marker.",
                    "expected_outcome": {
                        "summary": "README contains fixed marker.",
                        "acceptance_points": ["The marker is present."],
                    },
                    "hard_evaluation": {
                        "enabled": True,
                        "require_validation_pass": False,
                        "required_paths": ["README.md"],
                        "forbidden_paths": ["docs/notes.md"],
                        "expected_snippets": [
                            {"path": "README.md", "snippets": ["fixed marker"]}
                        ],
                        "forbidden_snippets": [
                            {"path": "README.md", "snippets": ["TODO"]}
                        ],
                        "command_checks": [
                            {
                                "label": "readme-marker",
                                "command": (
                                    f'"{sys.executable}" -c '
                                    "\"from pathlib import Path; "
                                    "print(Path('README.md').read_text())\""
                                ),
                                "expected": "fixed marker",
                            }
                        ],
                    },
                    "soft_evaluation": {
                        "enabled": True,
                        "mode": "payload-only",
                        "rubric": [
                            {
                                "name": "quality",
                                "weight": 1,
                                "description": "Patch is clear.",
                            }
                        ],
                    },
                }
            ]
        }
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup_policy="never",
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["hard_evaluation_status"] == "passed"
    assert result["hard_evaluation_score"] == result["hard_evaluation_max_score"]
    assert result["hard_evaluation_failed_checks"] == 0
    assert result["soft_evaluation_status"] == "payload_generated"
    hard = json.loads((run_dir / result["hard_evaluation_path"]).read_text(encoding="utf-8"))
    soft_payload_path = run_dir / result["soft_evaluation_payload_path"]
    soft = json.loads(soft_payload_path.read_text(encoding="utf-8"))
    assert hard["passed"] is True
    assert hard["summary"] == "passed"
    assert {check["name"] for check in hard["checks"]} >= {
        "required_path:README.md",
        "forbidden_paths",
        "expected_snippet:README.md",
        "forbidden_snippet:README.md",
        "command:readme-marker",
    }
    assert soft["task"]["prompt"] == "Add fixed marker."
    assert soft["expected_outcome"]["summary"] == "README contains fixed marker."
    assert soft["hard_evaluation"]["status"] == "passed"
    assert "fixed marker" in soft["patch_excerpt"]


def test_runner_hard_evaluation_deduplicates_repeated_snippet_checks(
    tmp_path: Path,
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "from pathlib import Path\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'fixed marker\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    task_file = TaskFile.model_validate(
        {
            "tasks": [
                {
                    "id": "hybrid-dedupe",
                    "prompt": "Add fixed marker.",
                    "expected_outcome": {
                        "files": [
                            {
                                "path": "README.md",
                                "expected_snippets": ["fixed marker"],
                                "forbidden_snippets": ["TODO"],
                            }
                        ],
                    },
                    "hard_evaluation": {
                        "enabled": True,
                        "expected_snippets": [
                            {"path": "README.md", "snippets": ["fixed marker"]}
                        ],
                        "forbidden_snippets": [
                            {"path": "README.md", "snippets": ["TODO"]}
                        ],
                    },
                }
            ]
        }
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup_policy="never",
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))
    hard = json.loads((run_dir / result["hard_evaluation_path"]).read_text(encoding="utf-8"))

    expected_checks = [
        check
        for check in hard["checks"]
        if check["name"] == "expected_snippet:README.md"
    ]
    forbidden_checks = [
        check
        for check in hard["checks"]
        if check["name"] == "forbidden_snippet:README.md"
    ]

    assert len(expected_checks) == 1
    assert len(forbidden_checks) == 1
    assert expected_checks[0]["evidence"]["snippet"] == "fixed marker"
    assert forbidden_checks[0]["evidence"]["snippet"] == "TODO"
    assert result["hard_evaluation_score"] == 3
    assert result["hard_evaluation_max_score"] == 3


def test_runner_hard_evaluation_reports_failed_required_and_forbidden_paths(
    tmp_path: Path,
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "from pathlib import Path\nPath('docs').mkdir(exist_ok=True)\n"
        "Path('docs/notes.md').write_text('unexpected\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    task_file = TaskFile.model_validate(
        {
            "tasks": [
                {
                    "id": "hybrid-fail",
                    "prompt": "Change README only.",
                    "hard_evaluation": {
                        "enabled": True,
                        "required_paths": ["README.md"],
                        "forbidden_paths": ["docs/notes.md"],
                        "max_changed_files": 1,
                    },
                }
            ]
        }
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup_policy="never",
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))
    hard = json.loads((run_dir / result["hard_evaluation_path"]).read_text(encoding="utf-8"))

    assert result["hard_evaluation_status"] == "failed"
    assert result["hard_evaluation_failed_checks"] >= 2
    failed = {check["name"] for check in hard["checks"] if check["status"] == "failed"}
    assert "required_path:README.md" in failed
    assert "forbidden_paths" in failed


def test_runner_writes_custom_prompt_template(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    prompt_template = tmp_path / "prompts" / "agent-task.md"
    prompt_template.parent.mkdir()
    prompt_template.write_text(
        "CUSTOM {task_id} {task_title} {variant} {repo_ref} {category} {difficulty}\n"
        "{task_prompt}",
        encoding="utf-8",
    )
    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('custom prompt run')\n", encoding="utf-8")
    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="custom-prompt",
                title="Custom Prompt",
                prompt="Use the custom prompt.",
                category="docs",
                difficulty="easy",
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )
    config.agent.prompt_template = prompt_template

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))
    prompt = (run_dir / result["prompt_path"]).read_text(encoding="utf-8")

    assert result["status"] == "completed"
    assert prompt == (
        "CUSTOM custom-prompt Custom Prompt baseline HEAD docs easy\n"
        "Use the custom prompt."
    )


def test_runner_rejects_unknown_prompt_template_variable_before_agent_runs(
    tmp_path: Path,
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    prompt_template = tmp_path / "prompts" / "agent-task.md"
    prompt_template.parent.mkdir()
    prompt_template.write_text("Unknown {missing}", encoding="utf-8")
    sentinel_path = tmp_path / "agent-ran.txt"
    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        f"from pathlib import Path\nPath({str(sentinel_path)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    task_file = TaskFile(tasks=[TaskConfig(id="bad-template", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )
    config.agent.prompt_template = prompt_template

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "internal_error"
    assert result["prompt_path"] is None
    assert any(
        "prompt template references unknown variable: missing" in error
        for error in result["errors"]
    )
    assert not sentinel_path.exists()


def test_runner_does_not_fail_case_when_json_telemetry_file_is_missing(
    tmp_path: Path,
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text(
        "from pathlib import Path\n"
        "p = Path('README.md')\n"
        "p.write_text(p.read_text(encoding='utf-8') + 'no telemetry\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    task_file = TaskFile(tasks=[TaskConfig(id="missing-telemetry", prompt="Append a line.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )
    config.agent.telemetry = AgentTelemetryConfig(collector="json-file")

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert result["telemetry_status"] == "unavailable"
    assert result["telemetry_source"] == "json-file"
    assert "telemetry file not found" in result["telemetry_error"]
    assert not any("telemetry collection failed" in error for error in result["errors"])


def test_runner_marks_validation_failure(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    validation_script = tmp_path / "validate.py"
    validation_script.write_text("raise SystemExit(1)\n", encoding="utf-8")

    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="failing-validation",
                prompt="Do nothing.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{validation_script}"']),
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "validation_failed"
    assert result["validation_status"] == "failed"
    assert result["confidence"] == "medium"
    assert result["validation_results"][0]["exit_code"] == 1


def test_runner_applies_config_validation_timeout_to_task_commands(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    validation_script = tmp_path / "slow_validate.py"
    validation_script.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")

    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="slow-validation",
                prompt="Do nothing.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{validation_script}"']),
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )
    config.evaluation.timeout_seconds = 1

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "validation_failed"
    assert result["validation_status"] == "failed"
    assert result["validation_results"][0]["timeout"] is True
    assert result["validation_results"][0]["exit_code"] is None


def test_runner_task_validation_timeout_overrides_config_default(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    validation_script = tmp_path / "slow_validate.py"
    validation_script.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")

    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="override-timeout",
                prompt="Do nothing.",
                validation=ValidationConfig(
                    commands=[f'"{sys.executable}" "{validation_script}"'],
                    timeout_seconds=1,
                ),
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )
    config.evaluation.timeout_seconds = 30

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "validation_failed"
    assert result["validation_status"] == "failed"
    assert result["validation_results"][0]["timeout"] is True


def test_runner_records_overlay_failure(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    agent_script = tmp_path / "agent.py"
    agent_script.write_text("raise SystemExit(0)\n", encoding="utf-8")
    missing_overlay = tmp_path / "missing" / "AGENTS.md"
    task_file = TaskFile(tasks=[TaskConfig(id="overlay-fail", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=missing_overlay,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "overlay_failed"
    assert result["validation_status"] == "skipped"
    assert result["confidence"] == "low"
    assert result["errors"]


def test_runner_guards_unique_run_directories_for_same_second(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    task_file = TaskFile(tasks=[TaskConfig(id="same-second", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    class FrozenDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 1, 2, 3, 4, 5)

    monkeypatch.setattr("context_eval.runner.datetime", FrozenDateTime)

    first_run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        console=_quiet_console(),
    ).run()
    second_run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        console=_quiet_console(),
    ).run()

    assert first_run_dir != second_run_dir
    assert first_run_dir.name == "20260102-030405"
    assert second_run_dir.name == "20260102-030405-2"

    for run_dir in [first_run_dir, second_run_dir]:
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
        result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))
        assert metadata["run_id"] == run_dir.name
        assert result["run_id"] == run_dir.name


def test_runner_records_cleanup_skipped_when_workspace_is_retained(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    task_file = TaskFile(tasks=[TaskConfig(id="retain-workspace", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=False,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["workspace_retained"] is True
    assert result["cleanup_status"] == "skipped"
    assert (run_dir / result["workspace_path"]).exists()


def test_runner_records_cleanup_failure_without_hiding_result(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    task_file = TaskFile(tasks=[TaskConfig(id="cleanup-fails", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    def fail_cleanup(repo_path: Path, workspace: Path) -> None:
        raise RuntimeError("cannot remove workspace")

    monkeypatch.setattr("context_eval.runner.remove_workspace", fail_cleanup)

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert result["workspace_retained"] is True
    assert result["cleanup_status"] == "failed"
    assert (run_dir / result["workspace_path"]).exists()
    assert any("workspace cleanup failed" in error for error in result["errors"])


def test_runner_rejects_unknown_cleanup_policy(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command="agent -p {prompt_file}",
        overlay_source=overlay_source,
    )

    with pytest.raises(ValueError, match="unsupported cleanup policy"):
        ContextEvalRunner(
            config=config,
            tasks=TaskFile(tasks=[TaskConfig(id="known", prompt="Do nothing.")]),
            cleanup_policy="sometimes",
            console=_quiet_console(),
        )


def test_cleanup_policy_successful_removes_only_successful_workspaces(
    tmp_path: Path,
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    pass_script = tmp_path / "pass.py"
    pass_script.write_text("raise SystemExit(0)\n", encoding="utf-8")
    fail_script = tmp_path / "fail.py"
    fail_script.write_text("raise SystemExit(1)\n", encoding="utf-8")
    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="passes",
                prompt="Do nothing.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{pass_script}"']),
            ),
            TaskConfig(
                id="fails",
                prompt="Do nothing.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{fail_script}"']),
            ),
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup_policy="successful",
        console=_quiet_console(),
    ).run()
    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    by_task = {result["task_id"]: result for result in results}

    assert by_task["passes"]["status"] == "completed"
    assert by_task["passes"]["cleanup_status"] == "succeeded"
    assert by_task["passes"]["workspace_retained"] is False
    assert not (run_dir / by_task["passes"]["workspace_path"]).exists()
    assert by_task["fails"]["status"] == "validation_failed"
    assert by_task["fails"]["cleanup_status"] == "skipped"
    assert by_task["fails"]["workspace_retained"] is True
    assert (run_dir / by_task["fails"]["workspace_path"]).exists()


def test_cleanup_policy_failed_removes_only_failed_workspaces(
    tmp_path: Path,
) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('no changes')\n", encoding="utf-8")
    pass_script = tmp_path / "pass.py"
    pass_script.write_text("raise SystemExit(0)\n", encoding="utf-8")
    fail_script = tmp_path / "fail.py"
    fail_script.write_text("raise SystemExit(1)\n", encoding="utf-8")
    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="passes",
                prompt="Do nothing.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{pass_script}"']),
            ),
            TaskConfig(
                id="fails",
                prompt="Do nothing.",
                validation=ValidationConfig(commands=[f'"{sys.executable}" "{fail_script}"']),
            ),
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup_policy="failed",
        console=_quiet_console(),
    ).run()
    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    by_task = {result["task_id"]: result for result in results}

    assert by_task["passes"]["status"] == "completed"
    assert by_task["passes"]["cleanup_status"] == "skipped"
    assert by_task["passes"]["workspace_retained"] is True
    assert (run_dir / by_task["passes"]["workspace_path"]).exists()
    assert by_task["fails"]["status"] == "validation_failed"
    assert by_task["fails"]["cleanup_status"] == "succeeded"
    assert by_task["fails"]["workspace_retained"] is False
    assert not (run_dir / by_task["fails"]["workspace_path"]).exists()


def test_runner_records_workspace_failure_without_running_case_steps(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    sentinel_path = tmp_path / "agent-ran.txt"
    agent_script.write_text(
        f"from pathlib import Path\nPath({str(sentinel_path)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="missing-ref",
                prompt="Do nothing.",
                repo_ref="refs/heads/does-not-exist",
                validation=ValidationConfig(commands=["python -c \"raise SystemExit(42)\""]),
            )
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8"))

    assert result["status"] == "workspace_failed"
    assert result["workspace_path"] is None
    assert result["prompt_path"] is None
    assert result["stdout_path"] is None
    assert result["stderr_path"] is None
    assert result["validation_results"] == []
    assert result["validation_status"] == "skipped"
    assert result["cleanup_status"] == "skipped"
    assert result["workspace_retained"] is False
    assert result["errors"]
    assert not sentinel_path.exists()


def test_runner_repeats_selected_cases_for_trials(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('trial run')\n", encoding="utf-8")
    task_file = TaskFile(tasks=[TaskConfig(id="repeat", prompt="Do nothing.")])
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=overlay_source,
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        trials=2,
        cleanup=True,
        console=_quiet_console(),
    ).run()
    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert len(results) == 2
    assert [result["trial_index"] for result in results] == [1, 2]
    assert [result["case_id"] for result in results] == [
        "repeat__baseline__trial-1",
        "repeat__baseline__trial-2",
    ]
    assert len({result["prompt_path"] for result in results}) == 2
    assert len({result["stdout_path"] for result in results}) == 2
    assert len({result["patch_path"] for result in results}) == 2
    assert len({result["workspace_path"] for result in results}) == 2


def test_runner_writes_run_manifest_for_selected_case_matrix(tmp_path: Path) -> None:
    repo = _create_repo(tmp_path)
    baseline_overlay = tmp_path / "ctx" / "baseline" / "AGENTS.md"
    experiment_overlay = tmp_path / "ctx" / "experiment" / "AGENTS.md"
    baseline_overlay.parent.mkdir(parents=True)
    experiment_overlay.parent.mkdir(parents=True)
    baseline_overlay.write_text("# Baseline\n", encoding="utf-8")
    experiment_overlay.write_text("# Experiment\n", encoding="utf-8")

    agent_script = tmp_path / "agent.py"
    agent_script.write_text("print('manifest run')\n", encoding="utf-8")
    task_file = TaskFile(
        tasks=[
            TaskConfig(id="task-1", prompt="First."),
            TaskConfig(id="task-2", prompt="Second."),
            TaskConfig(id="task-3", prompt="Excluded."),
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command=f'"{sys.executable}" "{agent_script}"',
        overlay_source=baseline_overlay,
    )
    config.variants["experiment"] = VariantConfig(
        description="Experiment",
        overlays=[OverlayConfig(source=experiment_overlay, target="AGENTS.md")],
    )

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        max_tasks=2,
        variants=["experiment", "baseline"],
        trials=2,
        jobs=2,
        cleanup=True,
        console=_quiet_console(),
    ).run()

    manifest_text = (run_dir / "run_manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert manifest_text.endswith("\n")
    assert manifest_text.splitlines()[1] == '  "case_count": 8,'
    assert manifest["manifest_schema_version"] == "1"
    assert manifest["run_id"] == run_dir.name
    assert manifest["config_hash"] == metadata["config_hash"]
    assert manifest["config_path"] is None
    assert manifest["trials"] == 2
    assert manifest["jobs"] == 2
    assert manifest["cleanup_policy"] == "always"
    assert manifest["case_count"] == 8
    assert [task["id"] for task in manifest["tasks"]] == ["task-1", "task-2"]
    assert [variant["name"] for variant in manifest["variants"]] == [
        "experiment",
        "baseline",
    ]
    assert [case["case_id"] for case in manifest["case_matrix"]] == [
        "task-1__experiment__trial-1",
        "task-1__experiment__trial-2",
        "task-1__baseline__trial-1",
        "task-1__baseline__trial-2",
        "task-2__experiment__trial-1",
        "task-2__experiment__trial-2",
        "task-2__baseline__trial-1",
        "task-2__baseline__trial-2",
    ]

    for task in manifest["tasks"]:
        assert len(task["task_hash"]) == 16
        assert task["repo_ref"] == "HEAD"
    for variant in manifest["variants"]:
        assert len(variant["variant_hash"]) == 16
    assert "task-3" not in {task["id"] for task in manifest["tasks"]}

    results_by_case = {result["case_id"]: result for result in results}
    assert set(results_by_case) == {
        case["case_id"] for case in manifest["case_matrix"]
    }
    for case in manifest["case_matrix"]:
        result = results_by_case[case["case_id"]]
        assert case["task_hash"] == result["task_hash"]
        assert case["variant_hash"] == result["variant_hash"]
        assert case["task_id"] == result["task_id"]
        assert case["variant"] == result["variant"]
        assert case["trial_index"] == result["trial_index"]


def test_runner_expands_agents_map_before_tasks_variants_and_trials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    task_file = TaskFile(
        tasks=[
            TaskConfig(id="task-1", prompt="First."),
            TaskConfig(id="task-2", prompt="Second."),
            TaskConfig(id="task-3", prompt="Excluded."),
        ]
    )
    config = ContextEvalConfig(
        repo=RepoConfig(path=repo, base_ref="HEAD"),
        agents={
            "agent-a": AgentProfileConfig(kind="custom", command="agent-a -p {prompt_file}"),
            "agent-b": AgentProfileConfig(kind="custom", command="agent-b -p {prompt_file}"),
        },
        variants={
            "baseline": VariantConfig(description="Baseline"),
            "experiment": VariantConfig(description="Experiment"),
        },
        output_dir=tmp_path / "runs",
    )

    def fake_run_case(
        self: ContextEvalRunner,
        run_id: str,
        run_dir: Path,
        agent,
        task: TaskConfig,
        variant_name: str,
        trial_index: int,
    ) -> CaseResult:
        return CaseResult(
            run_id=run_id,
            case_id=self._case_id(
                task.id,
                variant_name,
                trial_index,
                agent_name=agent.config.name,
            ),
            task_id=task.id,
            variant=variant_name,
            trial_index=trial_index,
            repo_ref="HEAD",
            agent_name=agent.config.name,
            network=agent.config.network,
            status="completed",
            validation_status="passed",
            confidence="high",
        )

    monkeypatch.setattr(ContextEvalRunner, "_run_case", fake_run_case)

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        max_tasks=2,
        variants=["experiment", "baseline"],
        trials=2,
        jobs=2,
        cleanup=True,
        console=_quiet_console(),
    ).run()

    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert manifest["case_count"] == 16
    assert [agent["name"] for agent in manifest["agents"]] == ["agent-a", "agent-b"]
    assert [agent["name"] for agent in metadata["agents"]] == ["agent-a", "agent-b"]
    assert [case["case_id"] for case in manifest["case_matrix"]] == [
        "task-1__experiment__agent-a__trial-1",
        "task-1__experiment__agent-a__trial-2",
        "task-1__baseline__agent-a__trial-1",
        "task-1__baseline__agent-a__trial-2",
        "task-2__experiment__agent-a__trial-1",
        "task-2__experiment__agent-a__trial-2",
        "task-2__baseline__agent-a__trial-1",
        "task-2__baseline__agent-a__trial-2",
        "task-1__experiment__agent-b__trial-1",
        "task-1__experiment__agent-b__trial-2",
        "task-1__baseline__agent-b__trial-1",
        "task-1__baseline__agent-b__trial-2",
        "task-2__experiment__agent-b__trial-1",
        "task-2__experiment__agent-b__trial-2",
        "task-2__baseline__agent-b__trial-1",
        "task-2__baseline__agent-b__trial-2",
    ]
    assert [result["case_id"] for result in results] == [
        case["case_id"] for case in manifest["case_matrix"]
    ]
    assert [case["agent_name"] for case in manifest["case_matrix"][:8]] == ["agent-a"] * 8
    assert [case["agent_name"] for case in manifest["case_matrix"][8:]] == ["agent-b"] * 8
    assert [result["agent_name"] for result in results[:8]] == ["agent-a"] * 8
    assert [result["agent_name"] for result in results[8:]] == ["agent-b"] * 8
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "- Agent profiles: `agent-a`, `agent-b`" in report
    assert "## Agent Summary" in report


def test_runner_rejects_jobs_less_than_one(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command="agent -p {prompt_file}",
        overlay_source=overlay_source,
    )

    with pytest.raises(ValueError, match="jobs must be at least 1"):
        ContextEvalRunner(config=config, jobs=0, console=_quiet_console())


def test_runner_parallel_jobs_write_results_in_planned_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    overlay_source = tmp_path / "ctx" / "AGENTS.md"
    overlay_source.parent.mkdir()
    overlay_source.write_text("# Instructions\n", encoding="utf-8")
    task_file = TaskFile(
        tasks=[
            TaskConfig(id="task-1", prompt="First."),
            TaskConfig(id="task-2", prompt="Second."),
            TaskConfig(id="task-3", prompt="Third."),
        ]
    )
    config = _base_config(
        tmp_path=tmp_path,
        repo=repo,
        agent_command="agent -p {prompt_file}",
        overlay_source=overlay_source,
    )
    lock = threading.Lock()
    active_cases = 0
    max_active_cases = 0

    def fake_run_case(
        self: ContextEvalRunner,
        run_id: str,
        run_dir: Path,
        agent,
        task: TaskConfig,
        variant_name: str,
        trial_index: int,
    ) -> CaseResult:
        nonlocal active_cases, max_active_cases
        with lock:
            active_cases += 1
            max_active_cases = max(max_active_cases, active_cases)
        time.sleep(0.05 if task.id == "task-1" else 0.01)
        with lock:
            active_cases -= 1
        return CaseResult(
            run_id=run_id,
            case_id=f"{task.id}__{variant_name}",
            task_id=task.id,
            variant=variant_name,
            repo_ref="HEAD",
            agent_name=self.config.agent.name,
            network=self.config.agent.network,
            status="completed",
            validation_status="passed",
            confidence="high",
        )

    monkeypatch.setattr(ContextEvalRunner, "_run_case", fake_run_case)

    run_dir = ContextEvalRunner(
        config=config,
        tasks=task_file,
        jobs=2,
        console=_quiet_console(),
    ).run()

    results = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert max_active_cases == 2
    assert [result["task_id"] for result in results] == ["task-1", "task-2", "task-3"]
    assert [result["case_id"] for result in results] == [
        "task-1__baseline",
        "task-2__baseline",
        "task-3__baseline",
    ]
