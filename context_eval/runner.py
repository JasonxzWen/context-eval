from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console

from context_eval import __version__
from context_eval.adapters.command import CommandTemplateAgent
from context_eval.config import load_tasks
from context_eval.contexts.overlay import OverlayError, apply_overlays
from context_eval.evaluators.command import run_validation_commands
from context_eval.evaluators.diff import collect_git_diff, create_diff_baseline
from context_eval.hashing import stable_hash
from context_eval.models import (
    RESULT_SCHEMA_VERSION,
    CaseResult,
    ContextEvalConfig,
    TaskConfig,
    TaskFile,
)
from context_eval.prompt import render_prompt, write_prompt_file
from context_eval.reports.markdown import render_markdown_report
from context_eval.workspace import WorkspaceError, create_workspace, remove_workspace, slugify


class ContextEvalRunner:
    def __init__(
        self,
        *,
        config: ContextEvalConfig,
        tasks: TaskFile | None = None,
        tasks_path: Path | None = None,
        cleanup: bool = False,
        max_tasks: int | None = None,
        variants: list[str] | None = None,
        console: Console | None = None,
    ) -> None:
        self.config = config
        self.tasks = tasks or load_tasks(tasks_path or config.tasks)
        self.cleanup = cleanup
        self.max_tasks = max_tasks
        self.selected_variants = variants or []
        self.console = console or Console()
        self.config_hash = stable_hash(
            config.model_dump(mode="json", exclude={"output_dir"})
        )

    def run(self) -> Path:
        run_id, run_dir = self._allocate_run_dir(datetime.now().strftime("%Y%m%d-%H%M%S"))
        self._prepare_run_dir(run_dir)
        self._write_metadata(run_id, run_dir)

        results_path = run_dir / "results.jsonl"
        agent = CommandTemplateAgent(self.config.agent)
        tasks = self.tasks.tasks[: self.max_tasks] if self.max_tasks else self.tasks.tasks
        variant_names = self._variant_names()

        for task in tasks:
            for variant_name in variant_names:
                self.console.print(f"Running task={task.id} variant={variant_name}")
                result = self._run_case(run_id, run_dir, agent, task, variant_name)
                with results_path.open("a", encoding="utf-8") as handle:
                    handle.write(result.model_dump_json() + "\n")

        render_markdown_report(run_dir)
        return run_dir

    def _variant_names(self) -> list[str]:
        if not self.selected_variants:
            return list(self.config.variants.keys())
        unknown = [name for name in self.selected_variants if name not in self.config.variants]
        if unknown:
            raise ValueError(f"unknown variant(s): {', '.join(unknown)}")
        return self.selected_variants

    def _allocate_run_dir(self, base_run_id: str) -> tuple[str, Path]:
        suffix = 1
        while True:
            run_id = base_run_id if suffix == 1 else f"{base_run_id}-{suffix}"
            run_dir = self.config.output_dir / run_id
            try:
                run_dir.mkdir(parents=True, exist_ok=False)
                return run_id, run_dir
            except FileExistsError:
                suffix += 1

    def _prepare_run_dir(self, run_dir: Path) -> None:
        for child in ["logs", "patches", "prompts", "artifacts", "workspaces"]:
            (run_dir / child).mkdir(parents=True, exist_ok=True)

    def _write_metadata(self, run_id: str, run_dir: Path) -> None:
        metadata = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "context_eval_version": __version__,
            "run_id": run_id,
            "config_hash": self.config_hash,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "config_path": str(self.config.config_path) if self.config.config_path else None,
            "repo": {
                "path": str(self.config.repo.path),
                "base_ref": self.config.repo.base_ref,
            },
            "agent": {
                "name": self.config.agent.name,
                "command": self.config.agent.command,
                "timeout_minutes": self.config.agent.timeout_minutes,
                "network": self.config.agent.network,
            },
            "variants": {
                name: {
                    "description": variant.description,
                    "hash": stable_hash(variant.model_dump(mode="json")),
                }
                for name, variant in self.config.variants.items()
            },
        }
        (run_dir / "run_metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

    def _run_case(
        self,
        run_id: str,
        run_dir: Path,
        agent: CommandTemplateAgent,
        task: TaskConfig,
        variant_name: str,
    ) -> CaseResult:
        started = time.monotonic()
        repo_ref = task.repo_ref or self.config.repo.base_ref
        case_name = f"{slugify(task.id)}__{slugify(variant_name)}"
        prompt_path = run_dir / "prompts" / f"{case_name}.md"
        patch_path = run_dir / "patches" / f"{case_name}.patch"
        stdout_path = run_dir / "logs" / f"{case_name}.agent.stdout.log"
        stderr_path = run_dir / "logs" / f"{case_name}.agent.stderr.log"
        output_dir = run_dir / "artifacts" / case_name
        workspace: Path | None = None
        baseline_tree: str | None = None
        baseline_index: Path | None = None
        errors: list[str] = []

        result = CaseResult(
            run_id=run_id,
            config_hash=self.config_hash,
            task_hash=stable_hash(task.model_dump(mode="json")),
            variant_hash=stable_hash(self.config.variants[variant_name].model_dump(mode="json")),
            task_id=task.id,
            variant=variant_name,
            repo_ref=repo_ref,
            agent_name=self.config.agent.name,
            network=self.config.agent.network,
            status="internal_error",
        )

        try:
            workspace = create_workspace(
                self.config.repo.path,
                repo_ref,
                run_dir,
                task.id,
                variant_name,
            )
            result.workspace_path = self._rel(run_dir, workspace)

            try:
                apply_overlays(workspace, self.config.variants[variant_name].overlays)
            except OverlayError as exc:
                errors.append(str(exc))
                result.status = "overlay_failed"
                return self._finish_result(result, run_dir, started, errors)

            try:
                baseline_index = output_dir / "baseline.index"
                baseline_tree = create_diff_baseline(workspace, baseline_index)
            except Exception as exc:
                errors.append(f"diff baseline creation failed: {exc}")

            prompt = render_prompt(task, variant_name)
            write_prompt_file(prompt_path, task, variant_name)
            result.prompt_path = self._rel(run_dir, prompt_path)

            agent_result = agent.run(
                workspace=workspace,
                prompt=prompt,
                prompt_file=prompt_path,
                task=task,
                variant=variant_name,
                output_dir=output_dir,
                timeout_seconds=self.config.agent.timeout_minutes * 60,
            )
            stdout_path.write_text(agent_result.stdout, encoding="utf-8")
            stderr_path.write_text(agent_result.stderr, encoding="utf-8")
            result.stdout_path = self._rel(run_dir, stdout_path)
            result.stderr_path = self._rel(run_dir, stderr_path)
            result.agent_exit_code = agent_result.exit_code
            result.timeout = agent_result.timeout

            if agent_result.timeout:
                result.status = "timeout"
            elif agent_result.exit_code != 0:
                result.status = "agent_failed"
                errors.append(f"agent exited with code {agent_result.exit_code}")
            else:
                result.status = "completed"

            try:
                diff_stats = collect_git_diff(workspace, patch_path, baseline_tree, baseline_index)
                result.patch_path = self._rel(run_dir, patch_path)
                result.changed_files = diff_stats.changed_files
                result.insertions = diff_stats.insertions
                result.deletions = diff_stats.deletions
                result.touched_paths = diff_stats.touched_paths
            except Exception as exc:  # pragma: no cover - defensive artifact capture
                errors.append(f"diff collection failed: {exc}")

            commands = task.validation.commands or self.config.evaluation.commands
            if commands:
                validation_results = run_validation_commands(commands, workspace)
                result.validation_results = validation_results
                self._write_validation_logs(run_dir, case_name, validation_results)
                failed = any(item.timeout or item.exit_code != 0 for item in validation_results)
                result.validation_status = "failed" if failed else "passed"
                result.confidence = "medium" if failed else "high"
                if failed and result.status == "completed":
                    result.status = "validation_failed"
            else:
                result.validation_status = "skipped"
                result.confidence = "low"

            return self._finish_result(result, run_dir, started, errors)
        except WorkspaceError as exc:
            errors.append(str(exc))
            return self._finish_result(result, run_dir, started, errors)
        except Exception as exc:  # pragma: no cover - protects long batch runs
            errors.append(str(exc))
            return self._finish_result(result, run_dir, started, errors)
        finally:
            if self.cleanup and workspace is not None:
                remove_workspace(self.config.repo.path, workspace)

    def _finish_result(
        self,
        result: CaseResult,
        run_dir: Path,
        started: float,
        errors: list[str],
    ) -> CaseResult:
        result.duration_seconds = time.monotonic() - started
        result.errors = errors
        if result.patch_path is None:
            patch_path = (
                run_dir
                / "patches"
                / f"{slugify(result.task_id)}__{slugify(result.variant)}.patch"
            )
            if patch_path.exists():
                result.patch_path = self._rel(run_dir, patch_path)
        return result

    def _write_validation_logs(
        self,
        run_dir: Path,
        case_name: str,
        validation_results: list,
    ) -> None:
        for index, command_result in enumerate(validation_results):
            stdout_path = run_dir / "logs" / f"{case_name}.validation.{index}.stdout.log"
            stderr_path = run_dir / "logs" / f"{case_name}.validation.{index}.stderr.log"
            stdout_path.write_text(command_result.stdout, encoding="utf-8")
            stderr_path.write_text(command_result.stderr, encoding="utf-8")

    @staticmethod
    def _rel(run_dir: Path, path: Path) -> str:
        return path.resolve().relative_to(run_dir.resolve()).as_posix()
