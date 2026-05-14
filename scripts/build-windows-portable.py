from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


PACKAGE_PREFIX = "context-eval-windows-x64"
DEFAULT_PYTHON_VERSIONS = ("3.11", "3.12", "3.13")


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _find_app_wheel(dist_dir: Path) -> Path | None:
    wheels = sorted(dist_dir.glob("context_eval-*.whl"))
    if not wheels:
        return None
    return wheels[-1]


def _version_from_wheel(wheel: Path) -> str:
    name = wheel.name
    prefix = "context_eval-"
    suffix = "-py3-none-any.whl"
    if not name.startswith(prefix) or not name.endswith(suffix):
        raise ValueError(f"unsupported context-eval wheel name: {name}")
    return name[len(prefix) : -len(suffix)]


def _safe_rmtree(path: Path, *, root: Path) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"refusing to remove path outside output dir: {resolved_path}") from exc
    if resolved_path.exists():
        shutil.rmtree(resolved_path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\r\n")


def _cmd_launcher_text() -> str:
    return r"""@echo off
set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\start-context-eval.ps1"
if errorlevel 1 pause
"""


def _powershell_startup_text() -> str:
    return r"""$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Workspace = Join-Path $Root "workspace"
$Venv = Join-Path $Root ".venv"
$Wheelhouse = Join-Path $Root "wheelhouse"
$FrontendDist = Join-Path $Root "frontend\dist"
$MarkerPath = Join-Path $Venv "context-eval-wheel.txt"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$ContextEvalApp = Join-Path $Venv "Scripts\context-eval-app.exe"

function Write-StartupError {
    param([string]$Message)
    Write-Host ""
    Write-Host $Message -ForegroundColor Red
    Write-Host ""
}

function Test-PythonCandidate {
    param([string[]]$Command)

    $Executable = $Command[0]
    $Arguments = @()
    if ($Command.Count -gt 1) {
        $Arguments = $Command[1..($Command.Count - 1)]
    }
    $Probe = "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    & $Executable @Arguments -c $Probe *> $null
    return $LASTEXITCODE -eq 0
}

function Invoke-SelectedPython {
    param([string[]]$Arguments)

    $Executable = $script:PythonCommand[0]
    $Prefix = @()
    if ($script:PythonCommand.Count -gt 1) {
        $Prefix = $script:PythonCommand[1..($script:PythonCommand.Count - 1)]
    }
    & $Executable @Prefix @Arguments
}

$Candidates = @(
    @("py", "-3.13"),
    @("py", "-3.12"),
    @("py", "-3.11"),
    @("python")
)

$script:PythonCommand = $null
foreach ($Candidate in $Candidates) {
    try {
        if (Test-PythonCandidate -Command $Candidate) {
            $script:PythonCommand = $Candidate
            break
        }
    } catch {
        continue
    }
}

if ($null -eq $script:PythonCommand) {
    Write-StartupError "Python 3.11 or newer is required. Install Python from https://www.python.org/downloads/ and enable 'Add python.exe to PATH', then run Start Context Eval.cmd again."
    exit 1
}

if (-not (Test-Path (Join-Path $FrontendDist "index.html"))) {
    Write-StartupError "The bundled frontend is missing: $FrontendDist"
    exit 1
}

$AppWheel = Get-ChildItem -Path $Wheelhouse -Filter "context_eval-*.whl" |
    Sort-Object Name -Descending |
    Select-Object -First 1

if ($null -eq $AppWheel) {
    Write-StartupError "The bundled context-eval wheel is missing from $Wheelhouse"
    exit 1
}

New-Item -ItemType Directory -Force -Path $Workspace | Out-Null

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating private .venv..."
    Invoke-SelectedPython -Arguments @("-m", "venv", $Venv)
}

$InstalledWheel = ""
if (Test-Path $MarkerPath) {
    $InstalledWheel = Get-Content $MarkerPath -Raw
}

if (($InstalledWheel.Trim() -ne $AppWheel.Name) -or (-not (Test-Path $ContextEvalApp))) {
    Write-Host "Installing bundled context-eval package..."
    & $VenvPython -m pip install --no-index --find-links $Wheelhouse --force-reinstall $AppWheel.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-StartupError "Package installation failed. The wheelhouse may be incomplete."
        exit $LASTEXITCODE
    }
    Set-Content -Path $MarkerPath -Value $AppWheel.Name -Encoding UTF8
}

Write-Host "Starting context-eval local app..."
& $ContextEvalApp --workspace $Workspace --port 0 --frontend-dist $FrontendDist
exit $LASTEXITCODE
"""


def _readme_text(version: str) -> str:
    return f"""context-eval Windows portable package {version}

Double-click Start Context Eval.cmd to create or reuse the private .venv, install
the bundled wheelhouse, start the loopback local app, and open your browser.

Python 3.11 or newer is required on the machine. If startup fails, install
Python from https://www.python.org/downloads/ with 'Add python.exe to PATH'
enabled, then run Start Context Eval.cmd again.

The package stores local app files under this directory:

- .venv/: private Python environment created by the launcher
- workspace/: local evaluation workspace and generated run artifacts
- wheelhouse/: bundled context-eval wheel and dependency wheels
- frontend/dist/: bundled browser app

Boundaries:

- does not install coding agents
- does not install target repository dependencies
- does not run agent commands until you confirm a run in the local app
- does not call hosted context-eval services
- does not create Git tags
- does not publish packages
"""


def _python_abi_tag(version: str) -> str:
    return f"cp{version.replace('.', '')}"


def _download_dependency_wheels(
    wheel: Path,
    wheelhouse: Path,
    *,
    python_versions: tuple[str, ...],
) -> None:
    for version in python_versions:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--platform",
                "win_amd64",
                "--implementation",
                "cp",
                "--python-version",
                version,
                "--abi",
                _python_abi_tag(version),
                "--only-binary=:all:",
                "--dest",
                str(wheelhouse),
                str(wheel),
            ],
            check=True,
        )


def _build_archive(staging_root: Path, archive_path: Path) -> None:
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staging_root.rglob("*")):
            archive.write(path, path.relative_to(staging_root.parent).as_posix())


def build_windows_portable(
    *,
    dist_dir: Path,
    frontend_dist: Path,
    output_dir: Path,
    skip_dependency_download: bool,
    python_versions: tuple[str, ...] = DEFAULT_PYTHON_VERSIONS,
) -> Path:
    dist_dir = dist_dir.resolve()
    frontend_dist = frontend_dist.resolve()
    output_dir = output_dir.resolve()

    wheel = _find_app_wheel(dist_dir)
    if wheel is None:
        raise FileNotFoundError(f"missing wheel artifact in {dist_dir}")
    if not (frontend_dist / "index.html").exists():
        raise FileNotFoundError(f"missing frontend index.html in {frontend_dist}")

    version = _version_from_wheel(wheel)
    package_name = f"{PACKAGE_PREFIX}-{version}"
    build_root = output_dir / "_context_eval_portable_build"
    staging_root = build_root / package_name
    archive_path = output_dir / f"{package_name}.zip"

    output_dir.mkdir(parents=True, exist_ok=True)
    _safe_rmtree(staging_root, root=output_dir)
    staging_root.mkdir(parents=True)

    wheelhouse = staging_root / "wheelhouse"
    wheelhouse.mkdir()
    shutil.copy2(wheel, wheelhouse / wheel.name)
    if not skip_dependency_download:
        _download_dependency_wheels(
            wheel,
            wheelhouse,
            python_versions=python_versions,
        )

    shutil.copytree(frontend_dist, staging_root / "frontend" / "dist")
    _write_text(staging_root / "Start Context Eval.cmd", _cmd_launcher_text())
    _write_text(staging_root / "scripts" / "start-context-eval.ps1", _powershell_startup_text())
    _write_text(staging_root / "README.txt", _readme_text(version))
    (staging_root / "workspace").mkdir()

    _build_archive(staging_root, archive_path)
    _safe_rmtree(build_root, root=output_dir)
    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a Windows portable context-eval local app package.",
    )
    parser.add_argument("--dist-dir", required=True, type=Path)
    parser.add_argument("--frontend-dist", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--skip-dependency-download",
        action="store_true",
        help="Do not populate dependency wheels. Intended for local script tests only.",
    )
    parser.add_argument(
        "--python-version",
        action="append",
        dest="python_versions",
        choices=DEFAULT_PYTHON_VERSIONS,
        help=(
            "Windows CPython dependency wheel version to bundle. "
            "May be supplied more than once. Defaults to 3.11, 3.12, and 3.13."
        ),
    )
    args = parser.parse_args()
    python_versions = tuple(args.python_versions or DEFAULT_PYTHON_VERSIONS)

    try:
        archive = build_windows_portable(
            dist_dir=args.dist_dir,
            frontend_dist=args.frontend_dist,
            output_dir=args.output_dir,
            skip_dependency_download=args.skip_dependency_download,
            python_versions=python_versions,
        )
    except (FileNotFoundError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        return _fail(str(exc))

    print(f"Built {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
