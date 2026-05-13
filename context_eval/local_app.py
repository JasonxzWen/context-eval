from __future__ import annotations

import io
import json
import os
import re
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml
from rich.console import Console

from context_eval.config import (
    ConfigError,
    filter_tasks,
    validate_config_files,
)
from context_eval.config_editor import build_editable_model
from context_eval.export import agent_summary_rows, export_run_csv, export_run_json
from context_eval.inspect_run import _load_metadata, _load_results
from context_eval.models import (
    SUPPORTED_AGENT_COMMAND_VARIABLES,
    AgentConfig,
    CaseResult,
    ContextEvalConfig,
    TaskFile,
    render_agent_command_preview,
    validate_agent_command_template,
)
from context_eval.reporting import (
    has_telemetry_gap,
    is_failed_result,
    is_timeout_result,
    run_matrix_overview,
)
from context_eval.reports.markdown import render_markdown_report
from context_eval.runner import ContextEvalRunner
from context_eval.ui import render_local_ui


class LocalAppError(RuntimeError):
    """Raised when a local app request violates the local safety contract."""


def _contains_traversal(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return ".." in PurePosixPath(normalized).parts


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


class _PathGuard:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def resolve_workspace_path(self, value: str | Path, *, field: str) -> Path:
        raw = str(value).strip()
        if not raw:
            raise LocalAppError(f"{field} must not be empty")
        if _contains_traversal(raw):
            raise LocalAppError(f"{field} contains path traversal")
        path = Path(raw)
        resolved = path.resolve() if path.is_absolute() else (self.workspace_root / path).resolve()
        if not _is_relative_to(resolved, self.workspace_root):
            raise LocalAppError(f"{field} must stay inside the local app workspace")
        return resolved

    def require_safe_artifact_path(self, value: str | Path, *, field: str) -> Path:
        raw = str(value).strip()
        if not raw:
            raise LocalAppError(f"{field} must not be empty")
        if _contains_traversal(raw):
            raise LocalAppError(f"{field} contains path traversal")
        path = Path(raw)
        if path.is_absolute():
            raise LocalAppError(f"{field} must be a relative artifact path")
        return path


class _RunLogBuffer(io.TextIOBase):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunks: list[str] = []

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        with self._lock:
            self._chunks.append(text)
        return len(text)

    def flush(self) -> None:
        return None

    def lines(self) -> list[str]:
        with self._lock:
            text = "".join(self._chunks)
        return [line for line in text.splitlines() if line.strip()]


@dataclass
class _RunRecord:
    app_run_id: str
    status: str
    created_at: str
    plan: dict[str, Any]
    logs: _RunLogBuffer = field(default_factory=_RunLogBuffer)
    run_dir: Path | None = None
    error: str | None = None
    stop_requested: bool = False
    completed_at: str | None = None
    thread: threading.Thread | None = None


class LocalAppService:
    """Local-only app service used by the HTTP handler and tests."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        initial_config_path: Path | str | None = None,
        frontend_dist: Path | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.guard = _PathGuard(self.workspace_root)
        self.frontend_dist = frontend_dist
        self.initial_config_path = (
            self.guard.resolve_workspace_path(initial_config_path, field="config_path")
            if initial_config_path is not None
            else None
        )
        self._runs: dict[str, _RunRecord] = {}
        self._runs_lock = threading.Lock()

    def health(self) -> dict[str, Any]:
        frontend_available = bool(
            self.frontend_dist and (self.frontend_dist / "index.html").exists()
        )
        return {
            "ok": True,
            "mode": "local-app",
            "bind_default": "loopback",
            "workspace_root": str(self.workspace_root),
            "initial_config_path": (
                str(self.initial_config_path) if self.initial_config_path else None
            ),
            "frontend": "dist" if frontend_available else "fallback",
        }

    def load_config(self, *, config_path: str | Path | None = None) -> dict[str, Any]:
        path = self._config_path(config_path)
        config, tasks = self._load_config_and_tasks(path, strict=False, check_agents=False)
        tasks_path = self.guard.resolve_workspace_path(config.tasks, field="tasks_path")
        editable = build_editable_model(config, tasks)
        return {
            "ok": True,
            "config_path": str(path),
            "tasks_path": str(tasks_path),
            "config_yaml": path.read_text(encoding="utf-8"),
            "tasks_yaml": tasks_path.read_text(encoding="utf-8"),
            "editable": editable.model_dump(mode="json"),
            "resolved": {
                "repo_path": str(config.repo.path),
                "output_dir": str(config.output_dir),
                "agents": list(config.agent_profiles().keys()),
                "variants": list(config.variants.keys()),
                "tasks": [task.id for task in tasks.tasks],
            },
        }

    def save_config(
        self,
        *,
        config_path: str | Path,
        tasks_path: str | Path,
        config_yaml: str,
        tasks_yaml: str,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        config_dst = self.guard.resolve_workspace_path(config_path, field="config_path")
        tasks_dst = self.guard.resolve_workspace_path(tasks_path, field="tasks_path")
        if not overwrite:
            existing = [path for path in [config_dst, tasks_dst] if path.exists()]
            if existing:
                raise LocalAppError(
                    "refusing to overwrite existing file(s): "
                    + ", ".join(str(path) for path in existing)
                )

        self._validate_yaml_documents(config_yaml=config_yaml, tasks_yaml=tasks_yaml)
        config_dst.parent.mkdir(parents=True, exist_ok=True)
        tasks_dst.parent.mkdir(parents=True, exist_ok=True)
        config_dst.write_text(config_yaml, encoding="utf-8")
        tasks_dst.write_text(tasks_yaml, encoding="utf-8")
        return {
            "ok": True,
            "config_path": str(config_dst),
            "tasks_path": str(tasks_dst),
            "message": "Saved local config files",
        }

    def preflight(
        self,
        *,
        config_path: str | Path | None = None,
        tasks_path: str | Path | None = None,
        check_agents: bool = True,
    ) -> dict[str, Any]:
        path = self._config_path(config_path)
        tasks_override = (
            self.guard.resolve_workspace_path(tasks_path, field="tasks_path")
            if tasks_path is not None
            else None
        )
        config, tasks = self._load_config_and_tasks(
            path,
            tasks_override=tasks_override,
            strict=True,
            check_agents=check_agents,
        )
        self._assert_output_dir_safe(config)
        self._assert_output_dir_writable(config.output_dir)
        return {
            "ok": True,
            "checks": [
                "schema",
                "repo",
                "git_refs",
                "overlay_paths",
                "task_ids",
                "prompt_templates",
                "agent_command_variables",
                "agent_executables" if check_agents else "agent_executables_skipped",
                "output_dir_writable",
                "side_effect_free",
            ],
            "tasks": len(tasks.tasks),
            "agents": list(config.agent_profiles().keys()),
            "variants": list(config.variants.keys()),
            "output_dir": str(config.output_dir),
        }

    def plan_run(
        self,
        *,
        config_path: str | Path | None = None,
        tasks_path: str | Path | None = None,
        agents: list[str] | None = None,
        variants: list[str] | None = None,
        task_ids: list[str] | None = None,
        max_tasks: int | None = None,
        trials: int = 1,
        jobs: int = 1,
        cleanup_policy: str = "never",
    ) -> dict[str, Any]:
        path = self._config_path(config_path)
        tasks_override = (
            self.guard.resolve_workspace_path(tasks_path, field="tasks_path")
            if tasks_path is not None
            else None
        )
        config, tasks = self._load_config_and_tasks(path, tasks_override=tasks_override)
        if task_ids:
            tasks = filter_tasks(tasks, task_ids=task_ids)
        self._assert_output_dir_safe(config)
        cleanup = ContextEvalRunner.resolve_cleanup_policy(
            cleanup=False,
            cleanup_policy=cleanup_policy,
        )
        runner = ContextEvalRunner(
            config=config,
            tasks=tasks,
            cleanup_policy=cleanup,
            max_tasks=max_tasks,
            agents=agents,
            variants=variants,
            trials=trials,
            jobs=jobs,
            console=Console(file=io.StringIO(), force_terminal=False),
        )
        selected_tasks = runner.tasks.tasks[:max_tasks] if max_tasks else runner.tasks.tasks
        agent_profiles = runner._agent_profiles()
        variant_names = runner._variant_names()
        cases = []
        for agent_profile in agent_profiles:
            for task in selected_tasks:
                for variant_name in variant_names:
                    for trial_index in range(1, trials + 1):
                        agent_name = (
                            agent_profile.name if config.uses_agent_profile_map() else None
                        )
                        case_id = runner._case_id(
                            task.id,
                            variant_name,
                            trial_index,
                            agent_name=agent_name,
                        )
                        repo_ref = task.repo_ref or config.repo.base_ref
                        cases.append(
                            {
                                "case_id": case_id,
                                "agent_name": agent_profile.name,
                                "agent_kind": agent_profile.kind,
                                "task_id": task.id,
                                "variant": variant_name,
                                "trial_index": trial_index,
                                "repo_ref": repo_ref,
                                "prompt_path": f"prompts/{case_id}.md",
                                "command_preview": self._command_preview(
                                    config=config,
                                    agent_profile=agent_profile,
                                    task_id=task.id,
                                    variant=variant_name,
                                    case_id=case_id,
                                ),
                            }
                        )
        return {
            "ok": True,
            "config_path": str(path),
            "output_dir": str(config.output_dir),
            "cleanup_policy": cleanup,
            "jobs": jobs,
            "trials": trials,
            "case_count": len(cases),
            "agents": [profile.name for profile in agent_profiles],
            "tasks": [task.id for task in selected_tasks],
            "variants": variant_names,
            "cases": cases,
        }

    def start_run(
        self,
        *,
        confirm: bool,
        config_path: str | Path | None = None,
        tasks_path: str | Path | None = None,
        agents: list[str] | None = None,
        variants: list[str] | None = None,
        task_ids: list[str] | None = None,
        max_tasks: int | None = None,
        trials: int = 1,
        jobs: int = 1,
        cleanup_policy: str = "never",
    ) -> dict[str, Any]:
        if not confirm:
            raise LocalAppError("run start requires explicit confirmation")
        plan = self.plan_run(
            config_path=config_path,
            tasks_path=tasks_path,
            agents=agents,
            variants=variants,
            task_ids=task_ids,
            max_tasks=max_tasks,
            trials=trials,
            jobs=jobs,
            cleanup_policy=cleanup_policy,
        )
        app_run_id = uuid.uuid4().hex[:12]
        record = _RunRecord(
            app_run_id=app_run_id,
            status="queued",
            created_at=datetime.now().isoformat(timespec="seconds"),
            plan=plan,
        )
        with self._runs_lock:
            self._runs[app_run_id] = record

        thread = threading.Thread(
            target=self._run_worker,
            args=(
                record,
                {
                    "config_path": config_path,
                    "tasks_path": tasks_path,
                    "agents": agents,
                    "variants": variants,
                    "task_ids": task_ids,
                    "max_tasks": max_tasks,
                    "trials": trials,
                    "jobs": jobs,
                    "cleanup_policy": cleanup_policy,
                },
            ),
            daemon=True,
        )
        record.thread = thread
        thread.start()
        return self.get_run(app_run_id)

    def get_run(self, app_run_id: str) -> dict[str, Any]:
        record = self._require_run(app_run_id)
        completed_cases = self._completed_case_count(record.run_dir)
        summary = self._result_summary(record.run_dir) if record.run_dir else None
        return {
            "ok": True,
            "app_run_id": record.app_run_id,
            "status": record.status,
            "created_at": record.created_at,
            "completed_at": record.completed_at,
            "stop_requested": record.stop_requested,
            "error": record.error,
            "run_dir": str(record.run_dir) if record.run_dir else None,
            "case_count": record.plan.get("case_count", 0),
            "completed_cases": completed_cases,
            "plan": record.plan,
            "summary": summary,
        }

    def stop_run(self, app_run_id: str) -> dict[str, Any]:
        record = self._require_run(app_run_id)
        record.stop_requested = True
        if record.status in {"queued", "running"}:
            record.status = "stop_requested"
        return {
            "ok": True,
            "app_run_id": app_run_id,
            "status": record.status,
            "message": (
                "Stop requested. The current runner records the request but does not "
                "terminate an already running agent subprocess."
            ),
        }

    def run_logs(self, app_run_id: str) -> dict[str, Any]:
        record = self._require_run(app_run_id)
        files: list[dict[str, str]] = []
        if record.run_dir:
            logs_dir = record.run_dir / "logs"
            if logs_dir.exists():
                for path in sorted(logs_dir.glob("*.log")):
                    files.append(
                        {
                            "path": path.relative_to(record.run_dir).as_posix(),
                            "tail": self._tail_text(path),
                        }
                    )
        return {
            "ok": True,
            "app_run_id": app_run_id,
            "console": record.logs.lines()[-200:],
            "files": files,
        }

    def results(self, *, run_dir: str | Path) -> dict[str, Any]:
        path = self.guard.resolve_workspace_path(run_dir, field="run_dir")
        results = _load_results(path)
        metadata = _load_metadata(path)
        risks = {
            "failed": [
                self._case_payload(result) for result in results if is_failed_result(result)
            ],
            "timeouts": [
                self._case_payload(result) for result in results if is_timeout_result(result)
            ],
            "low_confidence": [
                self._case_payload(result) for result in results if result.confidence == "low"
            ],
            "telemetry_gaps": [
                self._case_payload(result) for result in results if has_telemetry_gap(result)
            ],
        }
        return {
            "ok": True,
            "run_dir": str(path),
            "metadata": metadata,
            "overview": run_matrix_overview(results),
            "cases": [self._case_payload(result) for result in results],
            "risks": risks,
            "agent_summaries": agent_summary_rows(results),
        }

    def read_artifact(self, *, run_dir: str | Path, artifact_path: str | Path) -> dict[str, Any]:
        root = self.guard.resolve_workspace_path(run_dir, field="run_dir")
        relative = self.guard.require_safe_artifact_path(artifact_path, field="artifact_path")
        path = (root / relative).resolve()
        if not _is_relative_to(path, root):
            raise LocalAppError("artifact_path must stay inside run_dir")
        if not path.exists() or not path.is_file():
            raise LocalAppError(f"artifact not found: {relative.as_posix()}")
        return {
            "ok": True,
            "run_dir": str(root),
            "path": relative.as_posix(),
            "content": path.read_text(encoding="utf-8", errors="replace"),
        }

    def export(self, *, run_dir: str | Path, export_format: str) -> dict[str, Any]:
        path = self.guard.resolve_workspace_path(run_dir, field="run_dir")
        if export_format == "csv":
            content = export_run_csv(path)
            media_type = "text/csv"
        elif export_format == "json":
            content = export_run_json(path)
            media_type = "application/json"
        elif export_format == "markdown":
            report_path = render_markdown_report(path)
            content = report_path.read_text(encoding="utf-8")
            media_type = "text/markdown"
        elif export_format == "html":
            with tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "context-eval-ui.html"
                render_local_ui(config_path=None, run_dir=path, output_path=output)
                content = output.read_text(encoding="utf-8")
            media_type = "text/html"
        else:
            raise LocalAppError(f"unsupported export format: {export_format}")
        return {
            "ok": True,
            "run_dir": str(path),
            "format": export_format,
            "media_type": media_type,
            "content": content,
        }

    def _config_path(self, value: str | Path | None) -> Path:
        if value is not None:
            return self.guard.resolve_workspace_path(value, field="config_path")
        if self.initial_config_path is not None:
            return self.initial_config_path
        return self.guard.resolve_workspace_path("context-eval.yaml", field="config_path")

    def _load_config_and_tasks(
        self,
        config_path: Path,
        *,
        tasks_override: Path | None = None,
        strict: bool = False,
        check_agents: bool = False,
    ) -> tuple[ContextEvalConfig, TaskFile]:
        config, tasks = validate_config_files(
            config_path,
            tasks_override,
            strict=strict,
            check_agents=check_agents,
        )
        source_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if isinstance(source_data, dict) and "output_dir" not in source_data:
            config.output_dir = (self.workspace_root / ".context-eval" / "runs").resolve()
        tasks_path = tasks_override or config.tasks
        self.guard.resolve_workspace_path(tasks_path, field="tasks_path")
        self._assert_output_dir_safe(config)
        return config, tasks

    def _validate_yaml_documents(self, *, config_yaml: str, tasks_yaml: str) -> None:
        try:
            config_data = yaml.safe_load(config_yaml)
            tasks_data = yaml.safe_load(tasks_yaml)
        except yaml.YAMLError as exc:
            raise LocalAppError(f"invalid YAML: {exc}") from exc
        if not isinstance(config_data, dict):
            raise LocalAppError("config YAML root must be a mapping")
        if not isinstance(tasks_data, dict):
            raise LocalAppError("tasks YAML root must be a mapping")
        self._validate_raw_config_paths(config_data)
        if "agent" in config_data and "agents" in config_data:
            raise LocalAppError("cannot set both top-level agent and agents")
        try:
            config = ContextEvalConfig.model_validate(config_data)
            TaskFile.model_validate(tasks_data)
        except Exception as exc:
            raise LocalAppError(str(exc)) from exc
        for field_path, profile in self._iter_agent_profiles(config):
            allowed = set(SUPPORTED_AGENT_COMMAND_VARIABLES)
            if profile.telemetry.collector != "json-file":
                allowed.discard("telemetry_file")
            try:
                validate_agent_command_template(profile.command, allowed_variables=allowed)
            except ValueError as exc:
                raise LocalAppError(f"{field_path}.command: {exc}") from exc

    def _validate_raw_config_paths(self, config_data: dict[str, Any]) -> None:
        for key in ["tasks", "output_dir"]:
            raw = config_data.get(key)
            if raw is None:
                continue
            if not isinstance(raw, str):
                raise LocalAppError(f"{key} must be a path string")
            if _contains_traversal(raw):
                raise LocalAppError(f"{key} contains path traversal")
            self.guard.resolve_workspace_path(raw, field=key)

    def _iter_agent_profiles(self, config: ContextEvalConfig) -> list[tuple[str, AgentConfig]]:
        if config.agents:
            return [
                (f"agents.{name}", profile.to_agent_config(name))
                for name, profile in config.agents.items()
            ]
        if config.agent is not None:
            return [("agent", config.agent)]
        return []

    def _assert_output_dir_safe(self, config: ContextEvalConfig) -> None:
        source_data = {}
        if config.config_path and config.config_path.exists():
            loaded = yaml.safe_load(config.config_path.read_text(encoding="utf-8"))
            source_data = loaded if isinstance(loaded, dict) else {}
        raw_output_dir = source_data.get("output_dir")
        if isinstance(raw_output_dir, str) and _contains_traversal(raw_output_dir):
            raise LocalAppError("output_dir contains path traversal")
        if not _is_relative_to(config.output_dir, self.workspace_root):
            raise LocalAppError("output_dir must stay inside the local app workspace")

    def _assert_output_dir_writable(self, output_dir: Path) -> None:
        current = output_dir if output_dir.exists() else output_dir.parent
        while not current.exists() and current != current.parent:
            current = current.parent
        if not current.exists() or not current.is_dir():
            raise LocalAppError(f"output_dir parent does not exist: {output_dir.parent}")
        if not os.access(current, os.W_OK):
            raise LocalAppError(f"output_dir parent is not writable: {current}")

    def _command_preview(
        self,
        *,
        config: ContextEvalConfig,
        agent_profile: AgentConfig,
        task_id: str,
        variant: str,
        case_id: str,
    ) -> str:
        output_dir = config.output_dir / "_planned_artifacts" / case_id
        telemetry_file = (
            output_dir / agent_profile.telemetry.file
            if agent_profile.telemetry.collector == "json-file"
            else None
        )
        return render_agent_command_preview(
            agent_profile.command,
            workspace=config.output_dir / "_planned_workspaces" / case_id,
            prompt="<prompt text>",
            prompt_file=config.output_dir / "_planned_prompts" / f"{case_id}.md",
            task_id=task_id,
            variant=variant,
            output_dir=output_dir,
            telemetry_file=telemetry_file,
        )

    def _run_worker(self, record: _RunRecord, options: dict[str, Any]) -> None:
        try:
            record.status = "running"
            config_path = self._config_path(options["config_path"])
            tasks_override = (
                self.guard.resolve_workspace_path(options["tasks_path"], field="tasks_path")
                if options["tasks_path"] is not None
                else None
            )
            config, tasks = self._load_config_and_tasks(
                config_path,
                tasks_override=tasks_override,
            )
            if options["task_ids"]:
                tasks = filter_tasks(tasks, task_ids=options["task_ids"])
            runner = ContextEvalRunner(
                config=config,
                tasks=tasks,
                cleanup_policy=options["cleanup_policy"],
                max_tasks=options["max_tasks"],
                agents=options["agents"],
                variants=options["variants"],
                trials=options["trials"],
                jobs=options["jobs"],
                console=Console(file=record.logs, force_terminal=False, width=120),
            )
            run_dir = runner.run()
            record.run_dir = run_dir
            record.status = "completed"
            record.completed_at = datetime.now().isoformat(timespec="seconds")
        except Exception as exc:  # pragma: no cover - defensive long-run boundary
            record.status = "failed"
            record.error = str(exc)
            record.completed_at = datetime.now().isoformat(timespec="seconds")

    def _require_run(self, app_run_id: str) -> _RunRecord:
        with self._runs_lock:
            record = self._runs.get(app_run_id)
        if record is None:
            raise LocalAppError(f"unknown run: {app_run_id}")
        return record

    def _completed_case_count(self, run_dir: Path | None) -> int:
        if run_dir is None:
            return 0
        results_path = run_dir / "results.jsonl"
        if not results_path.exists():
            return 0
        return len([line for line in results_path.read_text(encoding="utf-8").splitlines() if line])

    def _result_summary(self, run_dir: Path | None) -> dict[str, Any] | None:
        if run_dir is None or not (run_dir / "results.jsonl").exists():
            return None
        results = _load_results(run_dir)
        return run_matrix_overview(results)

    def _tail_text(self, path: Path, *, line_count: int = 200) -> str:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-line_count:])

    def _case_payload(self, result: CaseResult) -> dict[str, Any]:
        return result.model_dump(mode="json")


def create_local_app_server(
    *,
    workspace_root: Path,
    host: str = "127.0.0.1",
    port: int = 0,
    config_path: Path | str | None = None,
    frontend_dist: Path | None = None,
) -> ThreadingHTTPServer:
    service = LocalAppService(
        workspace_root=workspace_root,
        initial_config_path=config_path,
        frontend_dist=frontend_dist,
    )

    class Handler(_LocalAppHandler):
        local_app_service = service

    return ThreadingHTTPServer((host, port), Handler)


def serve_local_app(
    *,
    workspace_root: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    config_path: Path | str | None = None,
    frontend_dist: Path | None = None,
) -> None:
    server = create_local_app_server(
        workspace_root=workspace_root,
        host=host,
        port=port,
        config_path=config_path,
        frontend_dist=frontend_dist,
    )
    actual_host, actual_port = server.server_address
    print(f"Local app: http://{actual_host}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


class _LocalAppHandler(BaseHTTPRequestHandler):
    local_app_service: LocalAppService
    server_version = "context-eval-local-app/1"

    def log_message(self, format: str, *args: Any) -> None:
        return None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/"):
                self._handle_api_get(parsed.path, parse_qs(parsed.query))
                return
            self._serve_static(parsed.path)
        except Exception as exc:
            self._send_error(exc)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = self._read_json_body()
            self._handle_api_post(parsed.path, body)
        except Exception as exc:
            self._send_error(exc)

    def _handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
        service = self.local_app_service
        if path == "/api/health":
            self._send_json(service.health())
            return
        run_match = re.fullmatch(r"/api/runs/([^/]+)", path)
        if run_match:
            self._send_json(service.get_run(run_match.group(1)))
            return
        logs_match = re.fullmatch(r"/api/runs/([^/]+)/logs", path)
        if logs_match:
            self._send_json(service.run_logs(logs_match.group(1)))
            return
        if path == "/api/results":
            self._send_json(service.results(run_dir=self._query_one(query, "run_dir")))
            return
        if path == "/api/artifacts":
            self._send_json(
                service.read_artifact(
                    run_dir=self._query_one(query, "run_dir"),
                    artifact_path=self._query_one(query, "path"),
                )
            )
            return
        if path == "/api/exports":
            self._send_json(
                service.export(
                    run_dir=self._query_one(query, "run_dir"),
                    export_format=self._query_one(query, "format"),
                )
            )
            return
        raise LocalAppError(f"unknown endpoint: {path}")

    def _handle_api_post(self, path: str, body: dict[str, Any]) -> None:
        service = self.local_app_service
        if path == "/api/config/load":
            self._send_json(service.load_config(config_path=body.get("config_path")))
            return
        if path == "/api/config/save":
            self._send_json(
                service.save_config(
                    config_path=body.get("config_path", "context-eval.yaml"),
                    tasks_path=body.get("tasks_path", "tasks.yaml"),
                    config_yaml=body.get("config_yaml", ""),
                    tasks_yaml=body.get("tasks_yaml", ""),
                    overwrite=bool(body.get("overwrite", True)),
                )
            )
            return
        if path == "/api/preflight":
            self._send_json(
                service.preflight(
                    config_path=body.get("config_path"),
                    tasks_path=body.get("tasks_path"),
                    check_agents=bool(body.get("check_agents", True)),
                )
            )
            return
        if path == "/api/run-plan":
            self._send_json(service.plan_run(**self._run_options(body)))
            return
        if path == "/api/runs":
            self._send_json(
                service.start_run(
                    confirm=bool(body.get("confirm", False)),
                    **self._run_options(body),
                )
            )
            return
        stop_match = re.fullmatch(r"/api/runs/([^/]+)/stop", path)
        if stop_match:
            self._send_json(service.stop_run(stop_match.group(1)))
            return
        raise LocalAppError(f"unknown endpoint: {path}")

    def _run_options(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "config_path": body.get("config_path"),
            "tasks_path": body.get("tasks_path"),
            "agents": body.get("agents"),
            "variants": body.get("variants"),
            "task_ids": body.get("task_ids"),
            "max_tasks": body.get("max_tasks"),
            "trials": int(body.get("trials", 1)),
            "jobs": int(body.get("jobs", 1)),
            "cleanup_policy": body.get("cleanup_policy", "never"),
        }

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise LocalAppError("JSON body must be an object")
        return data

    def _query_one(self, query: dict[str, list[str]], key: str) -> str:
        values = query.get(key)
        if not values or values[0] == "":
            raise LocalAppError(f"missing query parameter: {key}")
        return values[0]

    def _serve_static(self, path: str) -> None:
        service = self.local_app_service
        frontend_dist = service.frontend_dist
        if frontend_dist and (frontend_dist / "index.html").exists():
            relative = path.lstrip("/") or "index.html"
            if _contains_traversal(relative):
                raise LocalAppError("static path contains path traversal")
            candidate = (frontend_dist / relative).resolve()
            if not _is_relative_to(candidate, frontend_dist) or not candidate.exists():
                candidate = frontend_dist / "index.html"
            media_type = self._media_type(candidate)
            self._send_bytes(candidate.read_bytes(), media_type=media_type)
            return
        self._send_bytes(_fallback_html().encode("utf-8"), media_type="text/html")

    def _media_type(self, path: Path) -> str:
        suffix = path.suffix.lower()
        return {
            ".html": "text/html",
            ".js": "text/javascript",
            ".css": "text/css",
            ".svg": "image/svg+xml",
            ".json": "application/json",
        }.get(suffix, "application/octet-stream")

    def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, *, media_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, exc: Exception) -> None:
        status = HTTPStatus.BAD_REQUEST
        if isinstance(exc, FileNotFoundError):
            status = HTTPStatus.NOT_FOUND
        message = str(exc)
        if isinstance(exc, (ConfigError, LocalAppError, ValueError, OSError)):
            self._send_json({"ok": False, "error": message}, status=int(status))
            return
        self._send_json(
            {"ok": False, "error": f"internal error: {message}"},
            status=int(HTTPStatus.INTERNAL_SERVER_ERROR),
        )


def _fallback_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Context Eval Local App</title>
</head>
<body>
  <main>
    <h1>Context Eval Local App</h1>
    <p>Frontend build output was not found. Run the frontend validation workflow.</p>
  </main>
</body>
</html>
"""
