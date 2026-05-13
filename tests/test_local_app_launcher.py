from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

from context_eval.launcher import (
    LauncherStartupError,
    build_launcher_startup,
    launch_local_app,
)


class _FakeServer:
    def __init__(self) -> None:
        self.server_address = ("127.0.0.1", 43210)
        self.served = False
        self.closed = False

    def serve_forever(self) -> None:
        self.served = True

    def server_close(self) -> None:
        self.closed = True


def test_pyproject_exposes_packaged_local_app_launcher_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["context-eval-app"] == "context_eval.launcher:main"


def test_launcher_startup_plan_uses_local_log_and_loopback_defaults(tmp_path: Path) -> None:
    workspace = tmp_path / "eval"
    workspace.mkdir()
    config_path = workspace / "context-eval.yaml"
    config_path.write_text("repo:\n  path: ./repo\n", encoding="utf-8")

    startup = build_launcher_startup(
        workspace_root=workspace,
        config_path="context-eval.yaml",
        frontend_dist=tmp_path / "missing-dist",
    )

    assert startup.workspace_root == workspace.resolve()
    assert startup.config_path == config_path.resolve()
    assert startup.log_path == workspace / ".context-eval" / "logs" / "local-app-launcher.log"
    assert startup.host == "127.0.0.1"
    assert startup.port == 8765
    assert startup.frontend_available is False
    assert startup.log_path.parent.is_dir()


def test_launcher_rejects_config_paths_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "eval"
    workspace.mkdir()
    outside_config = tmp_path / "outside.yaml"
    outside_config.write_text("repo:\n  path: ./repo\n", encoding="utf-8")

    with pytest.raises(LauncherStartupError, match="config path must stay inside"):
        build_launcher_startup(
            workspace_root=workspace,
            config_path=outside_config,
        )


def test_launcher_opens_browser_after_server_binds_and_writes_log(tmp_path: Path) -> None:
    workspace = tmp_path / "eval"
    workspace.mkdir()
    startup = build_launcher_startup(workspace_root=workspace, port=0)
    fake_server = _FakeServer()
    opened_urls: list[str] = []

    def server_factory(**kwargs: Any) -> _FakeServer:
        assert kwargs["workspace_root"] == workspace.resolve()
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 0
        return fake_server

    launch_local_app(
        startup,
        server_factory=server_factory,
        browser_open=opened_urls.append,
    )

    assert opened_urls == ["http://127.0.0.1:43210"]
    assert fake_server.served is True
    assert fake_server.closed is True
    assert "Local app: http://127.0.0.1:43210" in startup.log_path.read_text(
        encoding="utf-8"
    )


def test_launcher_writes_failure_diagnostics_before_raising(tmp_path: Path) -> None:
    workspace = tmp_path / "eval"
    workspace.mkdir()
    startup = build_launcher_startup(workspace_root=workspace)

    def server_factory(**_: Any) -> _FakeServer:
        raise OSError("port is busy")

    with pytest.raises(LauncherStartupError, match="port is busy"):
        launch_local_app(startup, server_factory=server_factory)

    log_text = startup.log_path.read_text(encoding="utf-8")
    assert "Startup failed" in log_text
    assert "port is busy" in log_text
