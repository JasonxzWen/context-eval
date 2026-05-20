from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from rich.console import Console

from context_eval import __version__
from context_eval.adapters.base import TelemetryCollectionResult
from context_eval.adapters.command import CommandTemplateAgent
from context_eval.config import load_tasks
from context_eval.contexts.overlay import OverlayError, apply_overlays
from context_eval.evaluators.command import run_validation_commands
from context_eval.evaluators.diff import collect_git_diff, create_diff_baseline
from context_eval.evaluators.hybrid import run_hard_evaluation, write_soft_evaluation_payload
from context_eval.hashing import stable_hash
from context_eval.models import (
    RESULT_SCHEMA_VERSION,
    AgentConfig,
    CaseResult,
    CleanupPolicy,
    ContextEvalConfig,
    TaskConfig,
    TaskFile,
)
from context_eval.prompt import render_prompt, write_prompt_file
from context_eval.reports.markdown import render_markdown_report
from context_eval.workspace import WorkspaceError, create_workspace, remove_workspace, slugify

RUN_MANIFEST_SCHEMA_VERSION = "1"


class ContextEvalRunner:
    def __init__(
        self,
        *,
        config: ContextEvalConfig,
        tasks: TaskFile | None = None,
        tasks_path: Path | None = None,
        cleanup: bool = False,
        cleanup_policy: CleanupPolicy | str | None = None,
        max_tasks: int | None = None,
        agents: list[str] | None = None,
        variants: list[str] | None = None,
        trials: int = 1,
        jobs: int = 1,
        console: Console | None = None,
    ) -> None:
        self.config = config
        if trials < 1:
            raise ValueError("trials must be at least 1")
        if jobs < 1:
            raise ValueError("jobs must be at least 1")
        self.cleanup_policy = self.resolve_cleanup_policy(
            cleanup=cleanup,
            cleanup_policy=cleanup_policy,
        )
        self.tasks = tasks or load_tasks(tasks_path or config.tasks)
        self.max_tasks = max_tasks
        self.selected_agents = agents or []
        self.selected_variants = variants or []
        self.trials = trials
        self.jobs = jobs
        self.console = console or Console()
        self.config_hash = stable_hash(
            config.model_dump(mode="json", exclude={"output_dir"})
        )

    def run(self) -> Path:
        run_id, run_dir = self._allocate_run_dir(datetime.now().strftime("%Y%m%d-%H%M%S"))
        self._prepare_run_dir(run_dir)
        agent_profiles = self._agent_profiles()
        self._write_metadata(run_id, run_dir, agent_profiles)

        results_path = run_dir / "results.jsonl"
        tasks = self.tasks.tasks[: self.max_tasks] if self.max_tasks else self.tasks.tasks
        variant_names = self._variant_names()
        case_plan = [
            (agent_profile, task, variant_name, trial_index)
            for agent_profile in agent_profiles
            for task in tasks
            for variant_name in variant_names
            for trial_index in range(1, self.trials + 1)
        ]
        self._write_manifest(run_id, run_dir, agent_profiles, tasks, variant_names, case_plan)

        for result in self._run_case_plan(run_id, run_dir, case_plan):
            with results_path.open("a", encoding="utf-8") as handle:
                handle.write(result.model_dump_json() + "\n")

        render_markdown_report(run_dir)
        return run_dir

    def _run_case_plan(
        self,
        run_id: str,
        run_dir: Path,
        case_plan: list[tuple[AgentConfig, TaskConfig, str, int]],
    ) -> list[CaseResult]:
        if self.jobs == 1:
            results = []
            for agent_profile, task, variant_name, trial_index in case_plan:
                self._print_case_start(agent_profile, task, variant_name, trial_index)
                results.append(
                    self._run_case(
                        run_id,
                        run_dir,
                        CommandTemplateAgent(agent_profile),
                        task,
                        variant_name,
                        trial_index,
                    )
                )
            return results

        futures = []
        with ThreadPoolExecutor(max_workers=self.jobs) as executor:
            for agent_profile, task, variant_name, trial_index in case_plan:
                self._print_case_start(agent_profile, task, variant_name, trial_index)
                agent = CommandTemplateAgent(agent_profile)
                futures.append(
                    executor.submit(
                        self._run_case,
                        run_id,
                        run_dir,
                        agent,
                        task,
                        variant_name,
                        trial_index,
                    )
                )
            return [future.result() for future in futures]

    def _print_case_start(
        self,
        agent_profile: AgentConfig,
        task: TaskConfig,
        variant_name: str,
        trial_index: int,
    ) -> None:
        self.console.print(
            f"Running agent={agent_profile.name} "
            f"task={task.id} variant={variant_name} trial={trial_index}"
        )

    def _agent_profiles(self) -> list[AgentConfig]:
        profiles = self.config.agent_profiles()
        if not self.selected_agents:
            return list(profiles.values())
        unknown = [name for name in self.selected_agents if name not in profiles]
        if unknown:
            raise ValueError(f"unknown agent profile(s): {', '.join(unknown)}")
        return [profiles[name] for name in self.selected_agents]

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

    def _write_metadata(
        self,
        run_id: str,
        run_dir: Path,
        agent_profiles: list[AgentConfig],
    ) -> None:
        primary_agent = agent_profiles[0]
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
            "agent": self._agent_metadata(primary_agent),
            "agents": [self._agent_metadata(profile) for profile in agent_profiles],
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

    def _write_manifest(
        self,
        run_id: str,
        run_dir: Path,
        agent_profiles: list[AgentConfig],
        tasks: list[TaskConfig],
        variant_names: list[str],
        case_plan: list[tuple[AgentConfig, TaskConfig, str, int]],
    ) -> None:
        manifest = {
            "manifest_schema_version": RUN_MANIFEST_SCHEMA_VERSION,
            "run_id": run_id,
            "config_hash": self.config_hash,
            "config_path": str(self.config.config_path) if self.config.config_path else None,
            "cleanup_policy": self.cleanup_policy,
            "jobs": self.jobs,
            "trials": self.trials,
            "case_count": len(case_plan),
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "category": task.category,
                    "difficulty": task.difficulty,
                    "repo_ref": task.repo_ref or self.config.repo.base_ref,
                    "task_hash": self._task_hash(task),
                }
                for task in tasks
            ],
            "variants": [
                {
                    "name": name,
                    "description": self.config.variants[name].description,
                    "variant_hash": self._variant_hash(name),
                }
                for name in variant_names
            ],
            "case_matrix": [
                {
                    "case_id": self._case_id(
                        task.id,
                        variant_name,
                        trial_index,
                        agent_name=(
                            agent_profile.name
                            if self.config.uses_agent_profile_map()
                            else None
                        ),
                    ),
                    "agent_name": agent_profile.name,
                    "task_id": task.id,
                    "variant": variant_name,
                    "trial_index": trial_index,
                    "repo_ref": task.repo_ref or self.config.repo.base_ref,
                    "task_hash": self._task_hash(task),
                    "variant_hash": self._variant_hash(variant_name),
                }
                for agent_profile, task, variant_name, trial_index in case_plan
            ],
        }
        if self.config.uses_agent_profile_map():
            manifest["agents"] = [
                {
                    "name": profile.name,
                    "kind": profile.kind,
                    "command": profile.command,
                    "timeout_minutes": profile.timeout_minutes,
                    "network": profile.network,
                    "telemetry": profile.telemetry.model_dump(mode="json"),
                }
                for profile in agent_profiles
            ]
        (run_dir / "run_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _run_case(
        self,
        run_id: str,
        run_dir: Path,
        agent: CommandTemplateAgent,
        task: TaskConfig,
        variant_name: str,
        trial_index: int,
    ) -> CaseResult:
        started = time.monotonic()
        agent_profile = agent.config
        case_agent_name = agent_profile.name if self.config.uses_agent_profile_map() else None
        repo_ref = task.repo_ref or self.config.repo.base_ref
        case_name = self._case_id(
            task.id,
            variant_name,
            trial_index,
            agent_name=case_agent_name,
        )
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
            task_hash=self._task_hash(task),
            variant_hash=self._variant_hash(variant_name),
            case_id=case_name,
            trial_index=trial_index,
            task_id=task.id,
            variant=variant_name,
            repo_ref=repo_ref,
            agent_name=agent_profile.name,
            network=agent_profile.network,
            status="internal_error",
        )

        try:
            workspace = create_workspace(
                self.config.repo.path,
                repo_ref,
                run_dir,
                task.id,
                variant_name,
                case_id=case_name,
            )
            result.workspace_path = self._rel(run_dir, workspace)
            result.workspace_retained = workspace.exists()

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

            prompt = render_prompt(
                task,
                variant_name,
                prompt_template=agent_profile.prompt_template,
                repo_ref=repo_ref,
            )
            write_prompt_file(
                prompt_path,
                task,
                variant_name,
                prompt_template=agent_profile.prompt_template,
                repo_ref=repo_ref,
            )
            result.prompt_path = self._rel(run_dir, prompt_path)

            agent_result = agent.run(
                workspace=workspace,
                prompt=prompt,
                prompt_file=prompt_path,
                task=task,
                variant=variant_name,
                output_dir=output_dir,
                timeout_seconds=agent_profile.timeout_minutes * 60,
            )
            result.agent_duration_seconds = agent_result.duration_seconds
            try:
                telemetry = agent.collect_telemetry(
                    workspace=workspace,
                    prompt_file=prompt_path,
                    task=task,
                    variant=variant_name,
                    output_dir=output_dir,
                    command_result=agent_result,
                )
                self._record_telemetry(result, telemetry, run_dir, output_dir)
            except Exception as exc:
                result.telemetry_status = "error"
                result.telemetry_source = "adapter"
                result.telemetry_error = str(exc)
                errors.append(f"telemetry collection failed: {exc}")
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
                validation_results = run_validation_commands(
                    commands,
                    workspace,
                    timeout_seconds=self._validation_timeout_seconds(task),
                )
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

            self._record_hybrid_evaluation(
                result=result,
                task=task,
                run_dir=run_dir,
                workspace=workspace,
            )
            return self._finish_result(result, run_dir, started, errors)
        except WorkspaceError as exc:
            errors.append(str(exc))
            result.status = "workspace_failed"
            return self._finish_result(result, run_dir, started, errors)
        except Exception as exc:  # pragma: no cover - protects long batch runs
            errors.append(str(exc))
            return self._finish_result(result, run_dir, started, errors)
        finally:
            if workspace is not None:
                self._record_cleanup(result, workspace, errors)

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
            fallback_case_id = f"{slugify(result.task_id)}__{slugify(result.variant)}"
            patch_path = run_dir / "patches" / f"{result.case_id or fallback_case_id}.patch"
            if patch_path.exists():
                result.patch_path = self._rel(run_dir, patch_path)
        return result

    def _case_id(
        self,
        task_id: str,
        variant_name: str,
        trial_index: int,
        *,
        agent_name: str | None = None,
    ) -> str:
        base = f"{slugify(task_id)}__{slugify(variant_name)}"
        if agent_name:
            base = f"{base}__{slugify(agent_name)}"
        if self.trials == 1:
            return base
        return f"{base}__trial-{trial_index}"

    def _validation_timeout_seconds(self, task: TaskConfig) -> int | None:
        if task.validation.timeout_seconds is not None:
            return task.validation.timeout_seconds
        return self.config.evaluation.timeout_seconds

    @staticmethod
    def _task_hash(task: TaskConfig) -> str:
        return stable_hash(task.model_dump(mode="json"))

    def _variant_hash(self, variant_name: str) -> str:
        return stable_hash(self.config.variants[variant_name].model_dump(mode="json"))

    @staticmethod
    def _agent_metadata(profile: AgentConfig) -> dict[str, object]:
        return {
            "name": profile.name,
            "kind": profile.kind,
            "command": profile.command,
            "timeout_minutes": profile.timeout_minutes,
            "network": profile.network,
            "telemetry": profile.telemetry.model_dump(mode="json"),
        }

    def _record_telemetry(
        self,
        result: CaseResult,
        telemetry: TelemetryCollectionResult,
        run_dir: Path,
        output_dir: Path,
    ) -> None:
        result.telemetry_status = telemetry.status
        result.telemetry_source = telemetry.source
        result.telemetry_error = telemetry.error
        if telemetry.agent_duration_seconds is not None:
            result.agent_duration_seconds = telemetry.agent_duration_seconds
        result.prompt_tokens = telemetry.prompt_tokens
        result.cached_input_tokens = telemetry.cached_input_tokens
        result.completion_tokens = telemetry.completion_tokens
        result.total_tokens = telemetry.total_tokens
        result.reasoning_tokens = telemetry.reasoning_tokens
        result.reasoning_step_count = telemetry.reasoning_step_count
        result.tool_call_count = telemetry.tool_call_count
        result.tool_calls_by_name = telemetry.tool_calls_by_name
        result.command_call_count = telemetry.command_call_count
        result.model_name = telemetry.model_name
        result.provider_name = telemetry.provider_name
        result.telemetry_evidence_gaps = telemetry.telemetry_evidence_gaps
        result.codex_events_path = self._telemetry_artifact_path(
            telemetry.codex_events_path,
            run_dir=run_dir,
            output_dir=output_dir,
        )
        result.codex_final_message_path = self._telemetry_artifact_path(
            telemetry.codex_final_message_path,
            run_dir=run_dir,
            output_dir=output_dir,
        )
        result.codex_error_reason = telemetry.codex_error_reason

    def _telemetry_artifact_path(
        self,
        path: str | None,
        *,
        run_dir: Path,
        output_dir: Path,
    ) -> str | None:
        if path is None:
            return None
        artifact_path = Path(path)
        if not artifact_path.is_absolute():
            artifact_path = output_dir / artifact_path
        return self._rel(run_dir, artifact_path)

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

    def _record_hybrid_evaluation(
        self,
        *,
        result: CaseResult,
        task: TaskConfig,
        run_dir: Path,
        workspace: Path | None,
    ) -> None:
        hard_evaluation = run_hard_evaluation(
            result=result,
            task=task,
            run_dir=run_dir,
            workspace=workspace,
        )
        write_soft_evaluation_payload(
            result=result,
            task=task,
            run_dir=run_dir,
            hard_evaluation=hard_evaluation,
        )

    def _record_cleanup(
        self,
        result: CaseResult,
        workspace: Path,
        errors: list[str],
    ) -> None:
        if not self._should_cleanup(result):
            result.cleanup_status = "skipped"
            result.workspace_retained = workspace.exists()
            return

        try:
            remove_workspace(self.config.repo.path, workspace)
        except Exception as exc:
            errors.append(f"workspace cleanup failed: {exc}")
            result.cleanup_status = "failed"
            result.workspace_retained = workspace.exists()
            result.errors = errors
            return

        result.workspace_retained = workspace.exists()
        if result.workspace_retained:
            errors.append("workspace cleanup failed: workspace still exists after cleanup")
            result.cleanup_status = "failed"
        else:
            result.cleanup_status = "succeeded"
        result.errors = errors

    def _should_cleanup(self, result: CaseResult) -> bool:
        if self.cleanup_policy == "never":
            return False
        if self.cleanup_policy == "always":
            return True

        successful = result.status == "completed" and result.validation_status != "failed"
        if self.cleanup_policy == "successful":
            return successful
        if self.cleanup_policy == "failed":
            return not successful
        raise AssertionError(f"unsupported cleanup policy: {self.cleanup_policy}")

    @staticmethod
    def resolve_cleanup_policy(
        *,
        cleanup: bool,
        cleanup_policy: CleanupPolicy | str | None,
    ) -> CleanupPolicy:
        if cleanup_policy is None:
            return "always" if cleanup else "never"
        if cleanup and cleanup_policy != "always":
            raise ValueError("--cleanup cannot be combined with a non-always cleanup policy")
        if cleanup_policy not in {"never", "always", "successful", "failed"}:
            raise ValueError(f"unsupported cleanup policy: {cleanup_policy}")
        return cleanup_policy

    @staticmethod
    def _rel(run_dir: Path, path: Path) -> str:
        return path.resolve().relative_to(run_dir.resolve()).as_posix()
