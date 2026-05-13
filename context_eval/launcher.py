from __future__ import annotations

import traceback
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Any

import typer
from rich.console import Console

from context_eval.local_app import create_local_app_server


class LauncherStartupError(RuntimeError):
    """Raised when the packaged local app launcher cannot start safely."""


@dataclass(frozen=True)
class LauncherStartup:
    workspace_root: Path
    host: str
    port: int
    config_path: Path | None
    frontend_dist: Path | None
    frontend_available: bool
    log_path: Path
    open_browser: bool


console = Console()


def _contains_traversal(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return ".." in PurePosixPath(normalized).parts


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _resolve_inside_workspace(root: Path, value: str | Path, *, field: str) -> Path:
    raw = str(value).strip()
    if not raw:
        raise LauncherStartupError(f"{field} must not be empty")
    if _contains_traversal(raw):
        raise LauncherStartupError(f"{field} contains path traversal")
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not _is_relative_to(resolved, root):
        raise LauncherStartupError(f"{field} must stay inside the launcher workspace")
    return resolved


def _default_frontend_dist() -> Path:
    return Path(__file__).resolve().parents[1] / "frontend" / "dist"


def _append_log(path: Path, message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{path.read_text(encoding='utf-8') if path.exists() else ''}"
        f"[{timestamp}] {message}\n",
        encoding="utf-8",
    )


def build_launcher_startup(
    *,
    workspace_root: Path,
    config_path: Path | str | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    frontend_dist: Path | None = None,
    log_dir: Path | None = None,
    open_browser: bool = True,
) -> LauncherStartup:
    workspace = Path(workspace_root).resolve()
    if workspace.exists() and not workspace.is_dir():
        raise LauncherStartupError("workspace must be a directory")
    workspace.mkdir(parents=True, exist_ok=True)

    resolved_config = None
    if config_path is not None:
        resolved_config = _resolve_inside_workspace(
            workspace,
            config_path,
            field="config path",
        )
        if not resolved_config.exists():
            raise LauncherStartupError(f"config path does not exist: {resolved_config}")

    resolved_log_dir = (
        _resolve_inside_workspace(workspace, log_dir, field="log dir")
        if log_dir is not None
        else workspace / ".context-eval" / "logs"
    )
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    resolved_frontend = frontend_dist if frontend_dist is not None else _default_frontend_dist()

    return LauncherStartup(
        workspace_root=workspace,
        host=host,
        port=port,
        config_path=resolved_config,
        frontend_dist=resolved_frontend,
        frontend_available=(resolved_frontend / "index.html").exists(),
        log_path=resolved_log_dir / "local-app-launcher.log",
        open_browser=open_browser,
    )


def launch_local_app(
    startup: LauncherStartup,
    *,
    server_factory: Callable[..., Any] = create_local_app_server,
    browser_open: Callable[[str], Any] | None = webbrowser.open,
    output: Console | None = None,
) -> None:
    active_console = output or console
    server = None
    _append_log(
        startup.log_path,
        f"Starting local app workspace={startup.workspace_root} host={startup.host} "
        f"port={startup.port} frontend_available={startup.frontend_available}",
    )
    try:
        server = server_factory(
            workspace_root=startup.workspace_root,
            host=startup.host,
            port=startup.port,
            config_path=startup.config_path,
            frontend_dist=startup.frontend_dist,
        )
        actual_host, actual_port = server.server_address
        url = f"http://{actual_host}:{actual_port}"
        _append_log(startup.log_path, f"Local app: {url}")
        active_console.print(f"[green]Local app:[/green] {url}")
        active_console.print(f"local app launcher log: {startup.log_path}")
        if startup.open_browser and browser_open is not None:
            browser_open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        _append_log(startup.log_path, "Stopped by user")
    except Exception as exc:
        _append_log(startup.log_path, f"Startup failed: {exc}\n{traceback.format_exc()}")
        raise LauncherStartupError(str(exc)) from exc
    finally:
        if server is not None:
            server.server_close()


def check_launcher_startup(startup: LauncherStartup, *, output: Console | None = None) -> None:
    active_console = output or console
    _append_log(
        startup.log_path,
        f"Startup preflight passed workspace={startup.workspace_root} host={startup.host} "
        f"port={startup.port} frontend_available={startup.frontend_available}",
    )
    active_console.print("[green]Launcher startup preflight passed[/green]")
    active_console.print(f"local app launcher log: {startup.log_path}")
    active_console.print(
        f"workspace={startup.workspace_root} host={startup.host} "
        f"port={startup.port} frontend_available={startup.frontend_available}"
    )


def launch_command(
    workspace: Annotated[
        Path,
        typer.Option(
            "--workspace",
            "-w",
            file_okay=False,
            help="Evaluation workspace root for local config and artifacts.",
        ),
    ] = Path("."),
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            dir_okay=False,
            help="Optional initial config path inside the workspace.",
        ),
    ] = None,
    host: Annotated[str, typer.Option("--host", help="Host interface.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=0, help="Local app port.")] = 8765,
    no_browser: Annotated[
        bool,
        typer.Option(
            "--no-browser",
            help="Start the server without opening a browser.",
        ),
    ] = False,
    log_dir: Annotated[
        Path | None,
        typer.Option(
            "--log-dir",
            file_okay=False,
            help="Optional launcher log directory inside the workspace.",
        ),
    ] = None,
    check_startup: Annotated[
        bool,
        typer.Option(
            "--check-startup",
            help="Validate launcher startup inputs, write diagnostics, and exit.",
        ),
    ] = False,
) -> None:
    """Start the local app server, open the browser, and record startup diagnostics."""
    startup: LauncherStartup | None = None
    try:
        startup = build_launcher_startup(
            workspace_root=workspace,
            config_path=config,
            host=host,
            port=port,
            log_dir=log_dir,
            open_browser=not no_browser,
        )
        if check_startup:
            check_launcher_startup(startup, output=console)
            return
        launch_local_app(startup, output=console)
    except LauncherStartupError as exc:
        console.print(f"[red]Startup failed:[/red] {exc}")
        if startup is not None:
            console.print(f"local app launcher log: {startup.log_path}")
        raise typer.Exit(code=1) from exc


def main() -> None:
    typer.run(launch_command)


if __name__ == "__main__":
    main()
