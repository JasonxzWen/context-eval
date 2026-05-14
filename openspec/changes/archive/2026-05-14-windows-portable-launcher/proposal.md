## Why

The released wheel exposes `context-eval-app`, but acceptance still requires a
user to create a Python environment, install the wheel, and run a command. The
first no-CLI product path should let a Windows user download one archive, unzip
it, and double-click a launcher while keeping the implementation inside the
current Python package boundary.

## What Changes

- Add a Windows portable zip builder that packages the built wheel, dependency
  wheelhouse, frontend build output, and a double-click startup script.
- Add a PowerShell startup script and `.cmd` wrapper that create a private venv,
  install from the bundled wheelhouse, create a local workspace, and launch the
  loopback app in the browser.
- Add a `context-eval-app --frontend-dist` option so the portable launcher can
  serve bundled frontend assets outside the Python wheel.
- Document the portable package build and user startup flow.

## Capabilities

### New Capabilities

- `windows-portable-launcher`: Windows zip packaging and one-click local app
  startup without manual venv or pip commands.

### Modified Capabilities

- None. This is a new packaging surface layered over existing local app and
  release workflows.

## Impact

- `scripts/build-windows-portable.py`: new release packaging helper.
- `context_eval/launcher.py`: accepts an explicit frontend asset directory.
- `docs/local-app-workflow.md`, `docs/release-checklist.md`, `README.md`, and
  release smoke docs: document the portable package boundary and acceptance.
- Tests verify archive contents, script behavior, docs, and launcher option
  wiring.
